from __future__ import annotations

from pathlib import Path


def ensure_logs_dir(output_dir: Path) -> Path:
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir
