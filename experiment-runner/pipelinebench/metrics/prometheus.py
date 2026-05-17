from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrometheusMetrics:
    avg_cpu_usage: float | None
    max_cpu_usage: float | None
    avg_memory_usage: float | None
    max_memory_usage: float | None
    pod_restart_count: float | None


class PrometheusClient:
    def __init__(self, base_url: str, step_seconds: int = 5) -> None:
        self.base_url = base_url.rstrip("/")
        self.step_seconds = step_seconds

    def collect_namespace_metrics(self, namespace: str, start: datetime, end: datetime) -> PrometheusMetrics:
        return self.collect_namespaces_metrics([namespace], start, end)

    def collect_namespaces_metrics(self, namespaces: list[str], start: datetime, end: datetime) -> PrometheusMetrics:
        namespace_selector = _namespace_selector(namespaces)
        cpu_values = self._query_range_values(
            f'sum(rate(container_cpu_usage_seconds_total{{{namespace_selector},container!="POD",container!=""}}[1m]))',
            start,
            end,
        )
        memory_values = self._query_range_values(
            f'sum(container_memory_working_set_bytes{{{namespace_selector},container!="POD",container!=""}})',
            start,
            end,
        )
        duration_seconds = max(int((end - start).total_seconds()), self.step_seconds)

        return PrometheusMetrics(
            avg_cpu_usage=_average(cpu_values),
            max_cpu_usage=max(cpu_values) if cpu_values else None,
            avg_memory_usage=_average(memory_values),
            max_memory_usage=max(memory_values) if memory_values else None,
            pod_restart_count=self._query_instant_scalar(
                f'sum(increase(kube_pod_container_status_restarts_total{{{namespace_selector}}}[{duration_seconds}s]))',
                end,
            ),
        )

    def _query_range_values(self, query: str, start: datetime, end: datetime) -> list[float]:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start.timestamp(),
                    "end": end.timestamp(),
                    "step": self.step_seconds,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            values: list[float] = []
            for series in payload.get("data", {}).get("result", []):
                for _, value in series.get("values", []):
                    values.append(float(value))
            if not values:
                LOGGER.warning("Prometheus range query returned no data: %s", query)
            return values
        except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
            LOGGER.warning("Prometheus range query failed: %s", exc)
            return []

    def _query_instant_scalar(self, query: str, timestamp: datetime) -> float | None:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": query, "time": timestamp.timestamp()},
                timeout=15,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            results = payload.get("data", {}).get("result", [])
            if not results:
                return None
            return float(results[0]["value"][1])
        except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
            LOGGER.warning("Prometheus query failed: %s", exc)
            return None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _namespace_selector(namespaces: list[str]) -> str:
    if not namespaces:
        raise ValueError("At least one namespace is required for Prometheus collection")
    if len(namespaces) == 1:
        return f'namespace="{namespaces[0]}"'
    pattern = "|".join(re.escape(namespace).replace("\\-", "-") for namespace in namespaces)
    return f'namespace=~"^({pattern})$"'
