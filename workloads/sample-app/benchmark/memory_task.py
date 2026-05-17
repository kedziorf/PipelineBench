from __future__ import annotations

import time


def run_memory_task(block_count: int = 32, block_size: int = 256_000) -> int:
    blocks = [bytearray((index % 251 for _ in range(block_size))) for index in range(block_count)]
    checksum = sum(block[0] for block in blocks) + sum(block[-1] for block in blocks)
    time.sleep(0.2)
    return checksum


def main() -> None:
    started = time.perf_counter()
    checksum = run_memory_task()
    duration = time.perf_counter() - started
    print(f"memory_task_checksum={checksum}")
    print(f"memory_task_duration_seconds={duration:.6f}")


if __name__ == "__main__":
    main()
