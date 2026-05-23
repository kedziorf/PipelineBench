from __future__ import annotations

import atexit
import logging
import os
import subprocess
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path

from pipelinebench.config import CISystemSettings, PipelineBenchConfig
from pipelinebench.providers.base import CICDProvider

LOGGER = logging.getLogger(__name__)


@dataclass
class ConcourseProvider(CICDProvider):
    config: PipelineBenchConfig
    system: CISystemSettings
    _logs: dict[str, str] = field(default_factory=dict)
    _statuses: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.base_url = os.getenv("CONCOURSE_URL", "http://localhost:30084").rstrip("/")
        self.target = os.getenv("CONCOURSE_TARGET", "pipelinebench")
        self.pipeline_name = os.getenv("CONCOURSE_PIPELINE", "pipelinebench-sample")
        self.job_name = os.getenv("CONCOURSE_JOB", "sample-app")
        self.fly = self.config.base_dir.parent / ".tools" / "bin" / "fly"
        self.service_name = os.getenv("CONCOURSE_SERVICE_NAME", "pipelinebench-concourse-web")

    def deploy(self) -> None:
        LOGGER.info("Assuming Concourse is installed by scripts/install-concourse.sh")

    def wait_until_ready(self) -> None:
        self._ensure_fly()
        self._login()
        repo_uri = os.getenv(
            "PIPELINEBENCH_GITEA_REPO_INTERNAL_URL",
            f"{self.config.gitea.internal_url}/{self.config.gitea.repository_owner}/{self.config.gitea.repository_name}.git",
        )
        pipeline_path = self.config.base_dir.parent / "pipelines" / "concourse" / "pipeline.yml"
        self._run(
            [
                str(self.fly),
                "-t",
                self.target,
                "set-pipeline",
                "--non-interactive",
                "--pipeline",
                self.pipeline_name,
                "--config",
                str(pipeline_path),
                "--var",
                f"repo_uri={repo_uri}",
            ]
        )
        self._run([str(self.fly), "-t", self.target, "unpause-pipeline", "--pipeline", self.pipeline_name], check=False)

    def trigger_pipeline(self, run_id: int) -> str:
        pipeline_id = self._pipeline_id(run_id)
        result = self._run(
            [
                str(self.fly),
                "-t",
                self.target,
                "trigger-job",
                "--job",
                f"{self.pipeline_name}/{self.job_name}",
                "--watch",
            ],
            check=False,
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        self._logs[pipeline_id] = output
        self._statuses[pipeline_id] = "SUCCESS" if result.returncode == 0 else "FAILURE"
        return pipeline_id

    def wait_for_pipeline(self, pipeline_id: str) -> str:
        return self._statuses.get(pipeline_id, "UNKNOWN")

    def collect_logs(self, pipeline_id: str, output_path: str) -> None:
        Path(output_path).write_text(self._logs.get(pipeline_id, ""), encoding="utf-8")

    def cleanup(self) -> None:
        LOGGER.info("Concourse cleanup keeps configured pipeline and worker state for benchmark reproducibility")

    def _ensure_fly(self) -> None:
        self._ensure_port_forward(self.system.namespace, self.service_name, 30084, 8080)
        if self.fly.exists():
            return
        self.fly.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.base_url}/api/v1/cli?arch=amd64&platform=linux"
        self._run(["curl", "-fsSL", url, "-o", str(self.fly)])
        self.fly.chmod(0o755)

    def _login(self) -> None:
        deadline = time.time() + self.config.experiment.timeout_seconds
        while time.time() < deadline:
            result = self._run(
                [
                    str(self.fly),
                    "-t",
                    self.target,
                    "login",
                    "--concourse-url",
                    self.base_url,
                    "--username",
                    os.getenv("CONCOURSE_USER", "test"),
                    "--password",
                    os.getenv("CONCOURSE_PASSWORD", "test"),
                ],
                check=False,
            )
            if result.returncode == 0:
                return
            time.sleep(5)
        raise TimeoutError("Concourse did not become ready before timeout")

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

    def _pipeline_id(self, run_id: int) -> str:
        label = f"warmup-{abs(run_id)}" if run_id < 0 else f"run-{run_id}"
        return f"concourse-{label}-{int(time.time())}"

    def _run(self, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        LOGGER.debug("Running command: %s", " ".join(command))
        return subprocess.run(command, check=check, capture_output=True, text=True)


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0
