from __future__ import annotations

from pipelinebench.config import PipelineBenchConfig
from pipelinebench.experiment import Experiment


def run(config: PipelineBenchConfig, tool_name: str) -> None:
    Experiment(config=config, tool_name=tool_name).run()
