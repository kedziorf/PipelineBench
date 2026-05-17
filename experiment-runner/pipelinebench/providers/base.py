from __future__ import annotations

from abc import ABC, abstractmethod


class CICDProvider(ABC):
    @abstractmethod
    def deploy(self) -> None:
        pass

    @abstractmethod
    def wait_until_ready(self) -> None:
        pass

    @abstractmethod
    def trigger_pipeline(self, run_id: int) -> str:
        pass

    @abstractmethod
    def wait_for_pipeline(self, pipeline_id: str) -> str:
        pass

    @abstractmethod
    def collect_logs(self, pipeline_id: str, output_path: str) -> None:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass
