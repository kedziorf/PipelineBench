from __future__ import annotations

import hashlib
import time


def run_cpu_task(iterations: int = 150_000) -> str:
    digest = b"pipelinebench"
    for index in range(iterations):
        digest = hashlib.sha256(digest + index.to_bytes(8, "little")).digest()
    return digest.hex()


def main() -> None:
    started = time.perf_counter()
    digest = run_cpu_task()
    duration = time.perf_counter() - started
    print(f"cpu_task_digest={digest}")
    print(f"cpu_task_duration_seconds={duration:.6f}")


if __name__ == "__main__":
    main()
