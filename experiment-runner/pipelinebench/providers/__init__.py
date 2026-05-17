from pipelinebench.config import CISystemSettings, PipelineBenchConfig
from pipelinebench.providers.base import CICDProvider
from pipelinebench.providers.jenkins import JenkinsProvider


def create_provider(config: PipelineBenchConfig, system: CISystemSettings) -> CICDProvider:
    if system.provider == "jenkins":
        return JenkinsProvider(config=config, system=system)
    raise ValueError(f"Provider is not implemented yet: {system.provider}")
