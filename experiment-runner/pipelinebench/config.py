from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExperimentSettings:
    name: str
    runs_per_tool: int
    warmup_runs: int
    timeout_seconds: int
    cleanup_between_runs: bool
    cleanup_between_tools: bool


@dataclass(frozen=True)
class MonitoringSettings:
    prometheus_url: str
    scrape_interval_seconds: int
    metrics_window_seconds: int


@dataclass(frozen=True)
class GiteaSettings:
    namespace: str
    external_url: str
    internal_url: str
    repository_owner: str
    repository_name: str
    username: str


@dataclass(frozen=True)
class ResultsSettings:
    output_dir: Path
    use_run_directories: bool
    latest_alias: bool
    export_csv: bool
    export_json: bool
    export_logs: bool


@dataclass(frozen=True)
class CISystemSettings:
    name: str
    enabled: bool
    namespace: str
    provider: str
    deployment_method: str
    metrics_namespaces: list[str] = field(default_factory=list)
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class PipelineBenchConfig:
    base_dir: Path
    experiment: ExperimentSettings
    monitoring: MonitoringSettings
    gitea: GiteaSettings
    results: ResultsSettings
    ci_systems: list[CISystemSettings]

    def get_ci_system(self, name: str) -> CISystemSettings:
        for system in self.ci_systems:
            if system.name == name:
                return system
        raise ValueError(f"Unknown CI/CD system: {name}")


def load_config(path: Path) -> PipelineBenchConfig:
    config_path = path.resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)

    experiment = ExperimentSettings(**raw["experiment"])
    monitoring = MonitoringSettings(**raw["monitoring"])
    gitea = GiteaSettings(**raw["gitea"])
    results_raw = raw["results"]
    results = ResultsSettings(
        output_dir=(config_path.parent / results_raw["output_dir"]).resolve(),
        use_run_directories=bool(results_raw.get("use_run_directories", True)),
        latest_alias=bool(results_raw.get("latest_alias", True)),
        export_csv=bool(results_raw["export_csv"]),
        export_json=bool(results_raw["export_json"]),
        export_logs=bool(results_raw["export_logs"]),
    )
    ci_systems = [CISystemSettings(**item) for item in raw["ci_systems"]]

    return PipelineBenchConfig(
        base_dir=config_path.parent.resolve(),
        experiment=experiment,
        monitoring=monitoring,
        gitea=gitea,
        results=results,
        ci_systems=ci_systems,
    )
