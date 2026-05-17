from __future__ import annotations

import json
from pathlib import Path

from pipelinebench.metrics.aggregation import BenchmarkResult


def export_json(results: list[BenchmarkResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump([result.to_dict() for result in results], handle, indent=2)
