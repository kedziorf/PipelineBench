from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, median, stdev


@dataclass(frozen=True)
class BenchmarkResult:
    tool_name: str
    run_id: int
    pipeline_status: str
    start_time: str
    end_time: str
    duration_seconds: float
    avg_cpu_usage: float | None
    max_cpu_usage: float | None
    avg_memory_usage: float | None
    max_memory_usage: float | None
    pod_restart_count: float | None
    namespace: str
    logs_path: str
    error_message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkSummary:
    tool_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    duration_mean_seconds: float | None
    duration_median_seconds: float | None
    duration_min_seconds: float | None
    duration_max_seconds: float | None
    duration_stdev_seconds: float | None
    avg_cpu_usage_mean: float | None
    max_cpu_usage_peak: float | None
    avg_memory_usage_mean: float | None
    max_memory_usage_peak: float | None
    pod_restart_count_total: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def summarize_results(results: list[BenchmarkResult]) -> BenchmarkSummary:
    if not results:
        return BenchmarkSummary(
            tool_name="unknown",
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            success_rate=0.0,
            duration_mean_seconds=None,
            duration_median_seconds=None,
            duration_min_seconds=None,
            duration_max_seconds=None,
            duration_stdev_seconds=None,
            avg_cpu_usage_mean=None,
            max_cpu_usage_peak=None,
            avg_memory_usage_mean=None,
            max_memory_usage_peak=None,
            pod_restart_count_total=None,
        )

    successful_runs = sum(1 for result in results if result.pipeline_status == "SUCCESS")
    failed_runs = len(results) - successful_runs
    durations = [result.duration_seconds for result in results]
    avg_cpu_values = _present(result.avg_cpu_usage for result in results)
    max_cpu_values = _present(result.max_cpu_usage for result in results)
    avg_memory_values = _present(result.avg_memory_usage for result in results)
    max_memory_values = _present(result.max_memory_usage for result in results)
    restart_values = _present(result.pod_restart_count for result in results)

    return BenchmarkSummary(
        tool_name=results[0].tool_name,
        total_runs=len(results),
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=successful_runs / len(results),
        duration_mean_seconds=mean(durations),
        duration_median_seconds=median(durations),
        duration_min_seconds=min(durations),
        duration_max_seconds=max(durations),
        duration_stdev_seconds=stdev(durations) if len(durations) > 1 else 0.0,
        avg_cpu_usage_mean=_mean_or_none(avg_cpu_values),
        max_cpu_usage_peak=max(max_cpu_values) if max_cpu_values else None,
        avg_memory_usage_mean=_mean_or_none(avg_memory_values),
        max_memory_usage_peak=max(max_memory_values) if max_memory_values else None,
        pod_restart_count_total=sum(restart_values) if restart_values else None,
    )


def _present(values) -> list[float]:
    return [value for value in values if value is not None]


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return mean(values)
