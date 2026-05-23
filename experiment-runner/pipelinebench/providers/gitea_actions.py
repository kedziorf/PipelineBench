from __future__ import annotations

import atexit
import base64
import json
import sqlite3
import tempfile
import logging
import os
import subprocess
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from pipelinebench.config import CISystemSettings, PipelineBenchConfig
from pipelinebench.providers.base import CICDProvider

LOGGER = logging.getLogger(__name__)


@dataclass
class GiteaActionsProvider(CICDProvider):
    config: PipelineBenchConfig
    system: CISystemSettings

    def __post_init__(self) -> None:
        self.base_url = os.getenv("PIPELINEBENCH_GITEA_URL", self.config.gitea.external_url).rstrip("/")
        self.user = os.getenv("PIPELINEBENCH_GITEA_USER", self.config.gitea.username)
        self.password = os.getenv("PIPELINEBENCH_GITEA_PASSWORD", "pipelinebench-local-password")
        self.owner = self.config.gitea.repository_owner
        self.repo = self.config.gitea.repository_name
        self.session = requests.Session()
        self.session.auth = (self.user, self.password)

    def deploy(self) -> None:
        LOGGER.info("Assuming Gitea Actions and act_runner are installed by scripts/install-gitea-actions.sh")

    def wait_until_ready(self) -> None:
        self._ensure_port_forward("pipelinebench-gitea", "gitea-http", 30082, 3000)
        self._get(f"/api/v1/repos/{self.owner}/{self.repo}")
        self._run(["kubectl", "-n", self.system.namespace, "rollout", "status", "deployment/pipelinebench-gitea-actions-runner", "--timeout=5m"])

    def trigger_pipeline(self, run_id: int) -> str:
        timestamp = int(time.time())
        path = f".pipelinebench/gitea-actions/{timestamp}-{run_id}.txt"
        content = base64.b64encode(f"run_id={run_id}\ntimestamp={timestamp}\n".encode()).decode()
        payload = {
            "branch": "main",
            "content": content,
            "message": f"Trigger Gitea Actions benchmark run {run_id}",
            "author": {"name": "Filip Kedzior", "email": "filipkedzior@gmail.com"},
            "committer": {"name": "Filip Kedzior", "email": "filipkedzior@gmail.com"},
        }
        data = self._post(f"/api/v1/repos/{self.owner}/{self.repo}/contents/{path}", payload)
        commit_sha = data.get("commit", {}).get("sha")
        if not commit_sha:
            raise RuntimeError(f"Could not determine Gitea trigger commit: {data}")
        return str(commit_sha)

    def wait_for_pipeline(self, pipeline_id: str) -> str:
        deadline = time.time() + self.config.experiment.timeout_seconds
        while time.time() < deadline:
            run = self._find_run(pipeline_id)
            if run:
                status = int(run.get("status", 0))
                stopped = int(run.get("stopped", 0) or 0)
                if stopped > 0:
                    return "SUCCESS" if status == 1 else "FAILURE"
            time.sleep(5)
        raise TimeoutError(f"Gitea Actions run for commit {pipeline_id} timed out")

    def collect_logs(self, pipeline_id: str, output_path: str) -> None:
        payload: dict[str, Any] = {"commit_sha": pipeline_id, "run": self._find_run(pipeline_id)}
        result = self._run(
            ["kubectl", "-n", self.system.namespace, "logs", "deployment/pipelinebench-gitea-actions-runner", "--tail=300"],
            check=False,
        )
        payload["runner_logs"] = result.stdout
        if result.stderr:
            payload["runner_stderr"] = result.stderr
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def cleanup(self) -> None:
        LOGGER.info("Gitea Actions cleanup keeps runner registered for subsequent benchmark runs")

    def _find_run(self, commit_sha: str) -> dict[str, Any] | None:
        pod = self._gitea_pod_name()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "gitea.db"
            result = self._run(
                ["kubectl", "-n", "pipelinebench-gitea", "cp", f"{pod}:/var/lib/gitea/gitea.db", str(db_path)],
                check=False,
            )
            if result.returncode != 0 or not db_path.exists():
                return None
            connection = sqlite3.connect(db_path)
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                select id, title, commit_sha, status, started, stopped, created, updated
                from action_run
                where commit_sha = ?
                order by id desc
                limit 1
                """,
                (commit_sha,),
            ).fetchone()
            if row is None:
                return None
            return dict(row)

    def _gitea_pod_name(self) -> str:
        result = self._run(
            [
                "kubectl",
                "-n",
                "pipelinebench-gitea",
                "get",
                "pod",
                "-l",
                "app.kubernetes.io/name=pipelinebench-gitea",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ]
        )
        return result.stdout.strip()

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

    def _get(self, path: str) -> Any:
        response = self.session.get(f"{self.base_url}{path}", timeout=20)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def _run(self, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        LOGGER.debug("Running command: %s", " ".join(command))
        return subprocess.run(command, check=check, capture_output=True, text=True)


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0
