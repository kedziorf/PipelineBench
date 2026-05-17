from __future__ import annotations

from dataclasses import asdict, dataclass


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
