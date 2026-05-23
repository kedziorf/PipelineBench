from __future__ import annotations

import atexit
import base64
import json
import logging
import os
import re
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from pipelinebench.config import CISystemSettings, PipelineBenchConfig
from pipelinebench.providers.base import CICDProvider

LOGGER = logging.getLogger(__name__)


@dataclass
class WoodpeckerProvider(CICDProvider):
    config: PipelineBenchConfig
    system: CISystemSettings
    woodpecker_repo_id: int | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.gitea_url = os.getenv("PIPELINEBENCH_GITEA_URL", self.config.gitea.external_url).rstrip("/")
        self.gitea_user = os.getenv("PIPELINEBENCH_GITEA_USER", self.config.gitea.username)
        self.gitea_password = os.getenv("PIPELINEBENCH_GITEA_PASSWORD", "pipelinebench-local-password")
        self.owner = self.config.gitea.repository_owner
        self.repo = self.config.gitea.repository_name
        self.woodpecker_url = os.getenv("WOODPECKER_URL", "http://localhost:30086").rstrip("/")
        self.woodpecker_token = os.getenv("WOODPECKER_TOKEN", "")
        self.gitea_session = requests.Session()
        self.gitea_session.auth = (self.gitea_user, self.gitea_password)
        self.woodpecker_session = requests.Session()
        if self.woodpecker_token:
            self.woodpecker_session.headers.update({"Authorization": f"Bearer {self.woodpecker_token}"})

    def deploy(self) -> None:
        LOGGER.info("Assuming Woodpecker is installed by scripts/install-woodpecker.sh")

    def wait_until_ready(self) -> None:
        self._ensure_port_forward("pipelinebench-gitea", "gitea-http", 30082, 3000)
        self._ensure_port_forward(self.system.namespace, "woodpecker-server", 30086, 8000)
        self._run(["kubectl", "-n", self.system.namespace, "rollout", "status", "deployment/pipelinebench-woodpecker-server", "--timeout=5m"])
        self._run(["kubectl", "-n", self.system.namespace, "rollout", "status", "deployment/pipelinebench-woodpecker-agent", "--timeout=5m"], check=False)
        self._bootstrap_repo()

    def trigger_pipeline(self, run_id: int) -> str:
        timestamp = int(time.time())
        path = f".pipelinebench/woodpecker/{timestamp}-{run_id}.txt"
        content = base64.b64encode(f"run_id={run_id}\ntimestamp={timestamp}\n".encode()).decode()
        payload = {
            "branch": "main",
            "content": content,
            "message": f"Trigger Woodpecker benchmark run {run_id}",
            "author": {"name": "Filip Kedzior", "email": "filipkedzior@gmail.com"},
            "committer": {"name": "Filip Kedzior", "email": "filipkedzior@gmail.com"},
        }
        response = self.gitea_session.post(
            f"{self.gitea_url}/api/v1/repos/{self.owner}/{self.repo}/contents/{path}", json=payload, timeout=30
        )
        response.raise_for_status()
        commit_sha = response.json().get("commit", {}).get("sha")
        if not commit_sha:
            raise RuntimeError(f"Could not determine Woodpecker trigger commit: {response.text[:300]}")
        return str(commit_sha)

    def wait_for_pipeline(self, pipeline_id: str) -> str:
        return self._wait_with_api(pipeline_id)

    def collect_logs(self, pipeline_id: str, output_path: str) -> None:
        payload: dict[str, Any] = {"commit_sha": pipeline_id, "pipeline": self._find_pipeline(pipeline_id)}
        result = self._run(["kubectl", "-n", self.system.namespace, "logs", "deployment/pipelinebench-woodpecker-agent", "--tail=300"], check=False)
        payload["agent_logs"] = result.stdout
        if result.stderr:
            payload["agent_stderr"] = result.stderr
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def cleanup(self) -> None:
        self._run(["kubectl", "-n", self.system.namespace, "delete", "pod", "-l", "woodpecker-ci.org/repo-full-name", "--ignore-not-found=true"], check=False)

    def _bootstrap_repo(self) -> None:
        repo = self.gitea_session.get(f"{self.gitea_url}/api/v1/repos/{self.owner}/{self.repo}", timeout=30)
        repo.raise_for_status()
        gitea_repo_id = str(repo.json()["id"])

        if self.woodpecker_token:
            active_repo = self._activate_repo_with_token(gitea_repo_id)
        else:
            LOGGER.info("Bootstrapping Woodpecker OAuth session and local repository activation")
            active_repo = self._activate_repo_with_browser_session(gitea_repo_id)

        self.woodpecker_repo_id = int(active_repo["id"])
        LOGGER.info("Woodpecker repository active: %s (id=%s)", active_repo.get("full_name"), self.woodpecker_repo_id)

    def _activate_repo_with_token(self, gitea_repo_id: str) -> dict[str, Any]:
        active = self._lookup_active_repo(self.woodpecker_session)
        if active:
            return active
        response = self.woodpecker_session.post(f"{self.woodpecker_url}/api/repos", params={"forge_remote_id": gitea_repo_id}, timeout=60)
        response.raise_for_status()
        return dict(response.json())

    def _activate_repo_with_browser_session(self, gitea_repo_id: str) -> dict[str, Any]:
        browser = requests.Session()
        self._login_to_woodpecker(browser)
        csrf = self._woodpecker_csrf(browser)
        active = self._lookup_active_repo(browser)
        if not active:
            response = browser.post(
                f"{self.woodpecker_url}/api/repos",
                params={"forge_remote_id": gitea_repo_id},
                headers={"X-CSRF-TOKEN": csrf},
                timeout=60,
            )
            response.raise_for_status()
            active = dict(response.json())
        token_response = browser.post(f"{self.woodpecker_url}/api/user/token", headers={"X-CSRF-TOKEN": csrf}, timeout=30)
        token_response.raise_for_status()
        self.woodpecker_token = token_response.text.strip()
        self.woodpecker_session.headers.update({"Authorization": f"Bearer {self.woodpecker_token}"})
        return active

    def _login_to_woodpecker(self, browser: requests.Session) -> None:
        response = browser.get(f"{self.woodpecker_url}/authorize", allow_redirects=False, timeout=30)
        response.raise_for_status()
        location = response.headers.get("Location")
        if not location:
            raise RuntimeError("Woodpecker did not redirect to Gitea OAuth")

        response = browser.get(location, allow_redirects=False, timeout=30)
        if response.is_redirect:
            response = browser.get(urljoin(location, response.headers["Location"]), timeout=30)
        csrf = _required_field(response.text, "_csrf")
        response = browser.post(
            f"{self.gitea_url}/user/login",
            data={"_csrf": csrf, "user_name": self.gitea_user, "password": self.gitea_password},
            allow_redirects=False,
            timeout=30,
        )
        response.raise_for_status()

        authorize_url = urljoin(self.gitea_url, response.headers.get("Location", "/login/oauth/authorize"))
        response = browser.get(authorize_url, timeout=30)
        fields = _hidden_fields(response.text)
        if "client_id" in fields:
            grant_data = {key: fields.get(key, "") for key in ["_csrf", "client_id", "state", "scope", "nonce", "redirect_uri"]}
            grant_data["granted"] = "true"
            response = browser.post(f"{self.gitea_url}/login/oauth/grant", data=grant_data, allow_redirects=False, timeout=30)
            response.raise_for_status()

        for _ in range(10):
            if not response.is_redirect:
                break
            location = response.headers["Location"]
            if location.startswith("/"):
                location = urljoin(self.woodpecker_url, location)
            response = browser.get(location, allow_redirects=False, timeout=30)
            response.raise_for_status()

        user = browser.get(f"{self.woodpecker_url}/api/user", timeout=30)
        user.raise_for_status()

    def _woodpecker_csrf(self, browser: requests.Session) -> str:
        response = browser.get(f"{self.woodpecker_url}/web-config.js", timeout=30)
        response.raise_for_status()
        match = re.search(r'WOODPECKER_CSRF = "([^"]+)"', response.text)
        if not match:
            raise RuntimeError("Could not find Woodpecker CSRF token in web-config.js")
        return match.group(1)

    def _lookup_active_repo(self, session: requests.Session) -> dict[str, Any] | None:
        response = session.get(f"{self.woodpecker_url}/api/repos", timeout=30)
        response.raise_for_status()
        for repo in response.json():
            if repo.get("full_name") == f"{self.owner}/{self.repo}":
                return dict(repo)
        return None

    def _wait_with_api(self, commit_sha: str) -> str:
        timeout_seconds = self.system.timeout_seconds or self.config.experiment.timeout_seconds
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            pipeline = self._find_pipeline(commit_sha)
            if pipeline:
                status = str(pipeline.get("status", "")).lower()
                if status == "success":
                    return "SUCCESS"
                if status in {"failure", "error", "killed", "blocked", "declined"}:
                    return "FAILURE"
            time.sleep(5)
        raise TimeoutError(f"Woodpecker pipeline for commit {commit_sha} timed out after {timeout_seconds}s")

    def _find_pipeline(self, commit_sha: str) -> dict[str, Any] | None:
        if self.woodpecker_repo_id is None:
            return None
        response = self.woodpecker_session.get(f"{self.woodpecker_url}/api/repos/{self.woodpecker_repo_id}/pipelines", timeout=20)
        response.raise_for_status()
        for pipeline in response.json():
            pipeline_commit = str(pipeline.get("commit") or pipeline.get("commit_sha") or "")
            if pipeline_commit == commit_sha or pipeline_commit.startswith(commit_sha[:12]) or commit_sha.startswith(pipeline_commit[:12]):
                return dict(pipeline)
        return None

    def _ensure_port_forward(self, namespace: str, service: str, local_port: int, remote_port: int) -> None:
        if _port_open("127.0.0.1", local_port):
            return
        process = subprocess.Popen(
            ["kubectl", "-n", namespace, "port-forward", f"service/{service}", f"{local_port}:{remote_port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        atexit.register(lambda: process.terminate() if process.poll() is None else None)
        deadline = time.time() + 30
        while time.time() < deadline:
            if _port_open("127.0.0.1", local_port):
                return
            time.sleep(1)
        raise TimeoutError(f"Port-forward to {namespace}/{service} did not become ready")

    def _run(self, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        LOGGER.debug("Running command: %s", " ".join(command))
        return subprocess.run(command, check=check, capture_output=True, text=True)


def _hidden_fields(html: str) -> dict[str, str]:
    return dict(re.findall(r'name="([^"]+)" value="([^"]*)"', html))


def _required_field(html: str, name: str) -> str:
    fields = _hidden_fields(html)
    if name not in fields:
        raise RuntimeError(f"Could not find required form field {name}")
    return fields[name]


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0
