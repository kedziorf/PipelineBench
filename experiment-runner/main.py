from __future__ import annotations

import argparse
from pathlib import Path

from pipelinebench.cleanup import cleanup_provider
from pipelinebench.config import load_config
from pipelinebench.experiment import Experiment
from pipelinebench.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PipelineBench experiment runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a benchmark")
    run_parser.add_argument("--config", default="experiment-runner/config.yaml")
    run_parser.add_argument("--tool", default="jenkins")

    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup benchmark resources")
    cleanup_parser.add_argument("--config", default="experiment-runner/config.yaml")
    cleanup_parser.add_argument("--tool", default="jenkins")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging()
    config = load_config(Path(args.config))

    if args.command == "run":
      Experiment(config=config, tool_name=args.tool).run()
    elif args.command == "cleanup":
      cleanup_provider(config=config, tool_name=args.tool)


if __name__ == "__main__":
    main()
