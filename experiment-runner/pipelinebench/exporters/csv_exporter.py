from __future__ import annotations

import csv
from pathlib import Path

from pipelinebench.metrics.aggregation import BenchmarkResult


def export_csv(results: list[BenchmarkResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not results:
        return
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].to_dict().keys()))
        writer.writeheader()
        writer.writerows(result.to_dict() for result in results)
