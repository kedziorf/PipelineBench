from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from pipelinebench.config import CISystemSettings, PipelineBenchConfig
from pipelinebench.providers.base import CICDProvider

LOGGER = logging.getLogger(__name__)


@dataclass
class CircleCIProvider(CICDProvider):
    config: PipelineBenchConfig
    system: CISystemSettings

    def deploy(self) -> None:
        LOGGER.info("Assuming local CircleCI-compatible resources are installed by scripts/install-circleci.sh")

    def wait_until_ready(self) -> None:
        self._run(["kubectl", "-n", self.system.namespace, "get", "configmap", "pipelinebench-sample-workload"])
        self._run(["kubectl", "-n", self.system.namespace, "get", "configmap", "pipelinebench-circleci-config"])

    def trigger_pipeline(self, run_id: int) -> str:
        job_name = self._job_name(run_id)
        manifest = self._job_manifest(job_name, run_id)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False) as handle:
            handle.write(manifest)
            manifest_path = Path(handle.name)
        try:
            self._run(["kubectl", "apply", "-f", str(manifest_path)])
        finally:
            manifest_path.unlink(missing_ok=True)
        return job_name

    def wait_for_pipeline(self, pipeline_id: str) -> str:
        deadline = time.time() + self.config.experiment.timeout_seconds
        while time.time() < deadline:
            data = self._get_job(pipeline_id)
            for condition in data.get("status", {}).get("conditions", []):
                condition_type = condition.get("type")
                status = condition.get("status")
                if condition_type == "Complete" and status == "True":
                    return "SUCCESS"
                if condition_type == "Failed" and status == "True":
                    return "FAILURE"
            time.sleep(5)
        raise TimeoutError(f"CircleCI local Job {pipeline_id} timed out")

    def collect_logs(self, pipeline_id: str, output_path: str) -> None:
        result = self._run(
            [
                "kubectl",
                "-n",
                self.system.namespace,
                "logs",
                f"job/{pipeline_id}",
                "--all-containers=true",
                "--prefix=true",
            ],
            check=False,
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        Path(output_path).write_text(output, encoding="utf-8")

    def cleanup(self) -> None:
        self._run(
            [
                "kubectl",
                "-n",
                self.system.namespace,
                "delete",
                "job",
                "-l",
                "pipelinebench.io/experiment=sample-app",
                "--ignore-not-found=true",
            ],
            check=False,
        )

    def _get_job(self, name: str) -> dict:
        result = self._run(["kubectl", "-n", self.system.namespace, "get", "job", name, "-o", "json"])
        return json.loads(result.stdout)

    def _job_name(self, run_id: int) -> str:
        label = f"warmup-{abs(run_id)}" if run_id < 0 else f"run-{run_id}"
        return f"pipelinebench-circleci-{label}-{int(time.time())}"

    def _job_manifest(self, name: str, run_id: int) -> str:
        return f"""apiVersion: batch/v1
kind: Job
metadata:
  name: {name}
  namespace: {self.system.namespace}
  labels:
    pipelinebench.io/experiment: sample-app
    pipelinebench.io/tool: circleci
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        pipelinebench.io/experiment: sample-app
        pipelinebench.io/tool: circleci
        pipelinebench.io/job: {name}
    spec:
      restartPolicy: Never
      containers:
        - name: circleci-local
          image: python:3.12-slim
          env:
            - name: RUN_ID
              value: "{run_id}"
            - name: SAMPLE_APP_DIR
              value: /workspace/workloads/sample-app
            - name: PIPELINEBENCH_OBSERVATION_HOLD_SECONDS
              value: "20"
          volumeMounts:
            - name: sample-workload
              mountPath: /var/pipelinebench-workload
            - name: circleci-config
              mountPath: /workspace/.circleci/config.yml
              subPath: config.yml
          command:
            - /bin/sh
            - -ceu
            - |
              echo "PipelineBench CircleCI-compatible local run $RUN_ID"
              echo "--- CircleCI config ---"
              sed -n '1,220p' /workspace/.circleci/config.yml
              echo "--- prepare source ---"
              mkdir -p "$SAMPLE_APP_DIR/src" "$SAMPLE_APP_DIR/tests" "$SAMPLE_APP_DIR/benchmark"
              cp /var/pipelinebench-workload/requirements.txt "$SAMPLE_APP_DIR/requirements.txt"
              cp /var/pipelinebench-workload/app.py "$SAMPLE_APP_DIR/src/app.py"
              cp /var/pipelinebench-workload/test_app.py "$SAMPLE_APP_DIR/tests/test_app.py"
              cp /var/pipelinebench-workload/cpu_task.py "$SAMPLE_APP_DIR/benchmark/cpu_task.py"
              cp /var/pipelinebench-workload/memory_task.py "$SAMPLE_APP_DIR/benchmark/memory_task.py"
              cp /var/pipelinebench-workload/Dockerfile "$SAMPLE_APP_DIR/Dockerfile"
              find "$SAMPLE_APP_DIR" -maxdepth 3 -type f | sort
              echo "--- install dependencies ---"
              python3 -m pip install --user -r "$SAMPLE_APP_DIR/requirements.txt"
              echo "--- unit tests ---"
              PYTHONPATH="$SAMPLE_APP_DIR" python3 -m unittest discover -s "$SAMPLE_APP_DIR/tests"
              echo "--- cpu benchmark ---"
              python3 "$SAMPLE_APP_DIR/benchmark/cpu_task.py"
              echo "--- memory benchmark ---"
              python3 "$SAMPLE_APP_DIR/benchmark/memory_task.py"
              echo "--- docker build check ---"
              if command -v docker >/dev/null 2>&1; then
                docker build -t pipelinebench/sample-app:circleci-$RUN_ID "$SAMPLE_APP_DIR"
              else
                echo "Docker CLI is not available in this local CircleCI-compatible job; skipping image build."
              fi
              echo "--- observation hold ---"
              sleep "$PIPELINEBENCH_OBSERVATION_HOLD_SECONDS"
      volumes:
        - name: sample-workload
          configMap:
            name: pipelinebench-sample-workload
        - name: circleci-config
          configMap:
            name: pipelinebench-circleci-config
"""

    def _run(self, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        LOGGER.debug("Running command: %s", " ".join(command))
        return subprocess.run(command, check=check, capture_output=True, text=True)
