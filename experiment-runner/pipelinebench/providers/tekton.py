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
class TektonProvider(CICDProvider):
    config: PipelineBenchConfig
    system: CISystemSettings

    def deploy(self) -> None:
        LOGGER.info("Assuming Tekton is installed by scripts/install-tekton.sh")

    def wait_until_ready(self) -> None:
        self._run(["kubectl", "get", "crd", "pipelineruns.tekton.dev"])
        self._run(["kubectl", "-n", "tekton-pipelines", "wait", "deployment", "--all", "--for=condition=Available", "--timeout=5m"])
        self._run(["kubectl", "-n", self.system.namespace, "get", "pipeline", "pipelinebench-sample"])

    def trigger_pipeline(self, run_id: int) -> str:
        pipeline_run_name = self._pipeline_run_name(run_id)
        manifest = self._pipeline_run_manifest(pipeline_run_name, run_id)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False) as handle:
            handle.write(manifest)
            manifest_path = Path(handle.name)
        try:
            self._run(["kubectl", "apply", "-f", str(manifest_path)])
        finally:
            manifest_path.unlink(missing_ok=True)
        return pipeline_run_name

    def wait_for_pipeline(self, pipeline_id: str) -> str:
        deadline = time.time() + self.config.experiment.timeout_seconds
        while time.time() < deadline:
            data = self._get_pipeline_run(pipeline_id)
            for condition in data.get("status", {}).get("conditions", []):
                if condition.get("type") != "Succeeded":
                    continue
                status = condition.get("status")
                if status == "True":
                    return "SUCCESS"
                if status == "False":
                    return "FAILURE"
            time.sleep(5)
        raise TimeoutError(f"Tekton PipelineRun {pipeline_id} timed out")

    def collect_logs(self, pipeline_id: str, output_path: str) -> None:
        result = self._run(
            [
                "kubectl",
                "-n",
                self.system.namespace,
                "logs",
                "-l",
                f"tekton.dev/pipelineRun={pipeline_id}",
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
                "pipelinerun",
                "-l",
                "pipelinebench.io/experiment=sample-app",
                "--ignore-not-found=true",
            ],
            check=False,
        )

    def _get_pipeline_run(self, name: str) -> dict:
        result = self._run(["kubectl", "-n", self.system.namespace, "get", "pipelinerun", name, "-o", "json"])
        return json.loads(result.stdout)

    def _pipeline_run_name(self, run_id: int) -> str:
        label = f"warmup-{abs(run_id)}" if run_id < 0 else f"run-{run_id}"
        return f"pipelinebench-sample-{label}-{int(time.time())}"

    def _pipeline_run_manifest(self, name: str, run_id: int) -> str:
        return f"""apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: {name}
  namespace: {self.system.namespace}
  labels:
    pipelinebench.io/experiment: sample-app
    pipelinebench.io/tool: tekton
spec:
  pipelineRef:
    name: pipelinebench-sample
  params:
    - name: run-id
      value: "{run_id}"
  taskRunTemplate:
    serviceAccountName: pipelinebench-tekton
"""

    def _run(self, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        LOGGER.debug("Running command: %s", " ".join(command))
        return subprocess.run(command, check=check, capture_output=True, text=True)
