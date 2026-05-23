#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_TOOLS = ("jenkins", "tekton", "concourse", "gitea-actions", "woodpecker")

PROVIDER_NOTES = {
    "jenkins": "Controller-based Jenkins deployment installed locally in kind with Helm.",
    "tekton": "Kubernetes-native Tekton Pipelines installation running locally in kind.",
    "concourse": "Concourse web, worker, and PostgreSQL deployed locally in kind.",
    "gitea-actions": "Local Gitea Actions with act_runner connected to the shared local Gitea forge.",
    "woodpecker": "Woodpecker server and agent deployed locally with the Kubernetes backend and shared local Gitea forge.",
}


@dataclass(frozen=True)
class ComparisonRow:
    tool_name: str
    run_directory: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate_percent: float
    duration_mean_seconds: float | None
    duration_median_seconds: float | None
    duration_min_seconds: float | None
    duration_max_seconds: float | None
    avg_cpu_usage_mean_cores: float | None
    max_cpu_usage_peak_cores: float | None
    avg_memory_usage_mean_mib: float | None
    max_memory_usage_peak_mib: float | None
    pod_restart_count_total: float | None
    warmup_runs_detected: int
    metrics_populated: bool
    notes: str

    def to_csv_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "run_directory": self.run_directory,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate_percent": _format_number(self.success_rate_percent),
            "duration_mean_seconds": _format_optional(self.duration_mean_seconds),
            "duration_median_seconds": _format_optional(self.duration_median_seconds),
            "duration_min_seconds": _format_optional(self.duration_min_seconds),
            "duration_max_seconds": _format_optional(self.duration_max_seconds),
            "avg_cpu_usage_mean_cores": _format_optional(self.avg_cpu_usage_mean_cores),
            "max_cpu_usage_peak_cores": _format_optional(self.max_cpu_usage_peak_cores),
            "avg_memory_usage_mean_mib": _format_optional(self.avg_memory_usage_mean_mib),
            "max_memory_usage_peak_mib": _format_optional(self.max_memory_usage_peak_mib),
            "pod_restart_count_total": _format_optional(self.pod_restart_count_total),
            "warmup_runs_detected": self.warmup_runs_detected,
            "metrics_populated": "yes" if self.metrics_populated else "no",
            "notes": self.notes,
        }


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    results_root = _resolve_path(args.results_root, repo_root)
    output_root = _resolve_path(args.output_dir, repo_root)

    run_dirs = _select_run_dirs(args, results_root, repo_root)
    rows = [_build_row(run_dir) for run_dir in run_dirs]
    _validate_rows(rows, args.expected_runs)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    comparison_dir = output_root / f"{timestamp}_comparison"
    processed_dir = comparison_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    csv_path = processed_dir / "comparison.csv"
    markdown_path = processed_dir / "comparison.md"
    metadata_path = comparison_dir / "metadata.json"

    _write_csv(rows, csv_path)
    _write_markdown(rows, markdown_path, args.expected_runs)
    _write_metadata(rows, metadata_path, timestamp, args.expected_runs)

    print(f"Wrote comparison CSV: {csv_path}")
    print(f"Wrote comparison Markdown: {markdown_path}")
    print(f"Wrote comparison metadata: {metadata_path}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare PipelineBench summary.json files across local providers."
    )
    parser.add_argument(
        "--run",
        action="append",
        dest="runs",
        default=[],
        help=(
            "Run directory to include. May be passed multiple times. "
            "Defaults to the latest run for each requested tool."
        ),
    )
    parser.add_argument(
        "--tool",
        action="append",
        dest="tools",
        default=[],
        help=(
            "Tool name to include when --run is not provided. May be passed multiple "
            "times. Defaults to jenkins, tekton, concourse, gitea-actions, woodpecker."
        ),
    )
    parser.add_argument(
        "--results-root",
        default="results/runs",
        help="Directory containing timestamped PipelineBench run directories.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/runs",
        help="Parent directory where the timestamped comparison run directory is written.",
    )
    parser.add_argument(
        "--expected-runs",
        type=int,
        default=5,
        help="Expected number of measured runs per provider.",
    )
    return parser.parse_args()


def _select_run_dirs(
    args: argparse.Namespace, results_root: Path, repo_root: Path
) -> list[Path]:
    if args.runs:
        return [_require_run_dir(_resolve_path(run, repo_root)) for run in args.runs]

    tools = args.tools or list(DEFAULT_TOOLS)
    return [_find_latest_run(results_root, tool) for tool in tools]


def _find_latest_run(results_root: Path, tool: str) -> Path:
    candidates = sorted(
        path
        for path in results_root.glob(f"*_{tool}")
        if path.is_dir() and (path / "processed" / "summary.json").is_file()
    )
    if not candidates:
        raise SystemExit(f"No run directory with processed/summary.json found for {tool}")
    return candidates[-1]


def _require_run_dir(path: Path) -> Path:
    if not path.is_dir():
        raise SystemExit(f"Run directory does not exist: {path}")
    if not (path / "processed" / "summary.json").is_file():
        raise SystemExit(f"Missing processed/summary.json in run directory: {path}")
    return path


def _build_row(run_dir: Path) -> ComparisonRow:
    summary = _read_json(run_dir / "processed" / "summary.json")
    tool_name = str(summary["tool_name"])
    warmup_runs = len(list((run_dir / "logs").glob("*warmup*.log")))
    avg_memory_mib = _bytes_to_mib(_optional_float(summary.get("avg_memory_usage_mean")))
    max_memory_mib = _bytes_to_mib(_optional_float(summary.get("max_memory_usage_peak")))
    metrics_populated = all(
        _optional_float(summary.get(field)) is not None
        for field in (
            "avg_cpu_usage_mean",
            "max_cpu_usage_peak",
            "avg_memory_usage_mean",
            "max_memory_usage_peak",
            "pod_restart_count_total",
        )
    )

    return ComparisonRow(
        tool_name=tool_name,
        run_directory=str(run_dir),
        total_runs=int(summary["total_runs"]),
        successful_runs=int(summary["successful_runs"]),
        failed_runs=int(summary["failed_runs"]),
        success_rate_percent=float(summary["success_rate"]) * 100.0,
        duration_mean_seconds=_optional_float(summary.get("duration_mean_seconds")),
        duration_median_seconds=_optional_float(summary.get("duration_median_seconds")),
        duration_min_seconds=_optional_float(summary.get("duration_min_seconds")),
        duration_max_seconds=_optional_float(summary.get("duration_max_seconds")),
        avg_cpu_usage_mean_cores=_optional_float(summary.get("avg_cpu_usage_mean")),
        max_cpu_usage_peak_cores=_optional_float(summary.get("max_cpu_usage_peak")),
        avg_memory_usage_mean_mib=avg_memory_mib,
        max_memory_usage_peak_mib=max_memory_mib,
        pod_restart_count_total=_optional_float(summary.get("pod_restart_count_total")),
        warmup_runs_detected=warmup_runs,
        metrics_populated=metrics_populated,
        notes=PROVIDER_NOTES.get(tool_name, "Local PipelineBench provider."),
    )


def _validate_rows(rows: list[ComparisonRow], expected_runs: int) -> None:
    warnings: list[str] = []
    for row in rows:
        if row.total_runs != expected_runs:
            warnings.append(
                f"{row.tool_name}: expected {expected_runs} measured runs, found {row.total_runs}"
            )
        if row.successful_runs != row.total_runs:
            warnings.append(
                f"{row.tool_name}: {row.failed_runs} measured run(s) did not succeed"
            )
        if row.warmup_runs_detected < 1:
            warnings.append(f"{row.tool_name}: no warmup log detected")
        if not row.metrics_populated:
            warnings.append(f"{row.tool_name}: one or more metric fields are missing")

    for warning in warnings:
        print(f"WARNING: {warning}")


def _write_csv(rows: list[ComparisonRow], output_path: Path) -> None:
    fieldnames = list(rows[0].to_csv_dict().keys()) if rows else []
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(row.to_csv_dict() for row in rows)


def _write_markdown(rows: list[ComparisonRow], output_path: Path, expected_runs: int) -> None:
    lines = [
        "# PipelineBench Provider Comparison",
        "",
        f"Generated at: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"Expected measured runs per provider: {expected_runs}",
        "",
        "| Provider | Runs | Success | Duration mean/median/min/max (s) | CPU mean/peak (cores) | Memory mean/peak (MiB) | Restarts | Warmup | Metrics |",
        "| --- | ---: | ---: | --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.tool_name,
                    str(row.total_runs),
                    f"{_format_number(row.success_rate_percent)}%",
                    " / ".join(
                        [
                            _format_optional(row.duration_mean_seconds),
                            _format_optional(row.duration_median_seconds),
                            _format_optional(row.duration_min_seconds),
                            _format_optional(row.duration_max_seconds),
                        ]
                    ),
                    " / ".join(
                        [
                            _format_optional(row.avg_cpu_usage_mean_cores),
                            _format_optional(row.max_cpu_usage_peak_cores),
                        ]
                    ),
                    " / ".join(
                        [
                            _format_optional(row.avg_memory_usage_mean_mib),
                            _format_optional(row.max_memory_usage_peak_mib),
                        ]
                    ),
                    _format_optional(row.pod_restart_count_total),
                    str(row.warmup_runs_detected),
                    "yes" if row.metrics_populated else "no",
                ]
            )
            + " |"
        )

    lines.extend(["", "## Run Directories", ""])
    for row in rows:
        lines.append(f"- {row.tool_name}: `{row.run_directory}`")

    lines.extend(["", "## Notes And Limitations", ""])
    for row in rows:
        lines.append(f"- {row.tool_name}: {row.notes}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_metadata(
    rows: list[ComparisonRow], output_path: Path, timestamp: str, expected_runs: int
) -> None:
    metadata = {
        "experiment_id": f"{timestamp}_comparison",
        "tool_name": "comparison",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "expected_runs": expected_runs,
        "source_run_directories": [row.run_directory for row in rows],
    }
    output_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_path(path: str, base: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _bytes_to_mib(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 1024 / 1024


def _format_optional(value: float | None) -> str:
    if value is None:
        return ""
    return _format_number(value)


def _format_number(value: float) -> str:
    return f"{value:.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
