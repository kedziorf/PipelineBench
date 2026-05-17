from pipelinebench.config import CISystemSettings, PipelineBenchConfig
from pipelinebench.providers.base import CICDProvider
from pipelinebench.providers.jenkins import JenkinsProvider
from pipelinebench.providers.tekton import TektonProvider


def create_provider(config: PipelineBenchConfig, system: CISystemSettings) -> CICDProvider:
    if system.provider == "jenkins":
        return JenkinsProvider(config=config, system=system)
    if system.provider == "tekton":
        return TektonProvider(config=config, system=system)
    raise ValueError(f"Provider is not implemented yet: {system.provider}")
