from __future__ import annotations

import json
import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from pipelinebench.config import CISystemSettings, PipelineBenchConfig


@dataclass(frozen=True)
class ToolVersion:
    name: str
    version: str | None
    error: str | None = None


@dataclass(frozen=True)
class ExperimentMetadata:
    experiment_id: str
    experiment_name: str
    tool_name: str
    namespace: str
    started_at: str
    run_directory: str
    python_version: str
    platform: str
    git_commit: str | None
    git_dirty: bool | None
    tool_versions: list[ToolVersion]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["tool_versions"] = [asdict(version) for version in self.tool_versions]
        return data


def create_experiment_metadata(
    config: PipelineBenchConfig,
    system: CISystemSettings,
    experiment_id: str,
    started_at: datetime,
    run_directory: Path,
) -> ExperimentMetadata:
    return ExperimentMetadata(
        experiment_id=experiment_id,
        experiment_name=config.experiment.name,
        tool_name=system.name,
        namespace=system.namespace,
        started_at=started_at.isoformat(),
        run_directory=str(run_directory),
        python_version=platform.python_version(),
        platform=platform.platform(),
        git_commit=_run_text(["git", "rev-parse", "HEAD"]).version,
        git_dirty=_git_dirty(),
        tool_versions=[
            _run_text(["docker", "--version"], "docker"),
            _run_text(["kind", "--version"], "kind"),
            _run_text(["kubectl", "version", "--client"], "kubectl"),
            _run_text(["helm", "version", "--short"], "helm"),
            _run_text(["kubectl", "version", "-o", "json"], "kubernetes"),
            *_provider_versions(system),
        ],
    )


def write_metadata(metadata: ExperimentMetadata, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata.to_dict(), handle, indent=2)


def make_experiment_id(tool_name: str, started_at: datetime) -> str:
    timestamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{tool_name}"


def _run_text(command: list[str], name: str | None = None) -> ToolVersion:
    label = name or command[0]
    env = os.environ.copy()
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
    except FileNotFoundError:
        return ToolVersion(name=label, version=None, error="command not found")
    except subprocess.CalledProcessError as exc:
        error = (exc.stderr or exc.stdout or "").strip()
        return ToolVersion(name=label, version=None, error=error[:500])
    return ToolVersion(name=label, version=completed.stdout.strip())


def _git_dirty() -> bool | None:
    status = _run_text(["git", "status", "--short"], "git_status")
    if status.error:
        return None
    return bool(status.version)


def _provider_versions(system: CISystemSettings) -> list[ToolVersion]:
    if system.provider == "jenkins":
        return [_run_text(["helm", "status", "pipelinebench-jenkins", "-n", system.namespace], "jenkins_helm_release")]
    if system.provider == "tekton":
        return [
            _run_text(
                [
                    "kubectl",
                    "-n",
                    "tekton-pipelines",
                    "get",
                    "deployment",
                    "tekton-pipelines-controller",
                    "-o",
                    "jsonpath={.metadata.labels.app\\.kubernetes\\.io/version}",
                ],
                "tekton_pipelines_version",
            )
        ]
    return []
