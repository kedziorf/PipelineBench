from __future__ import annotations


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def deterministic_score(values: list[int]) -> int:
    return sum((index + 1) * value for index, value in enumerate(values))


def main() -> None:
    print(normalize_text("  PipelineBench   Sample App  "))
    print(deterministic_score([3, 1, 4, 1, 5]))


if __name__ == "__main__":
    main()
