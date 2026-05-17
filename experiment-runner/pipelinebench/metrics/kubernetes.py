from __future__ import annotations

import logging
import subprocess

LOGGER = logging.getLogger(__name__)


def delete_completed_benchmark_pods(namespace: str) -> None:
    command = [
        "kubectl",
        "-n",
        namespace,
        "delete",
        "pod",
        "--field-selector=status.phase=Succeeded",
        "--ignore-not-found=true",
    ]
    try:
        subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        LOGGER.warning("kubectl is not installed; skipping pod cleanup")
