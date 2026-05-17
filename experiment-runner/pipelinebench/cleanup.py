from __future__ import annotations

import logging

from pipelinebench.config import PipelineBenchConfig
from pipelinebench.providers import create_provider

LOGGER = logging.getLogger(__name__)


def cleanup_provider(config: PipelineBenchConfig, tool_name: str) -> None:
    system = config.get_ci_system(tool_name)
    provider = create_provider(config, system)
    provider.cleanup()
    LOGGER.info("Cleanup completed for %s", tool_name)
