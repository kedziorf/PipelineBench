from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pipelinebench.config import PipelineBenchConfig
from pipelinebench.exporters import ensure_logs_dir, export_csv, export_json, export_summary_csv, export_summary_json
from pipelinebench.metadata import create_experiment_metadata, make_experiment_id, write_metadata
from pipelinebench.metrics import BenchmarkResult, PrometheusClient, summarize_results, utc_now
from pipelinebench.metrics.kubernetes import delete_completed_benchmark_pods
from pipelinebench.providers import create_provider

LOGGER = logging.getLogger(__name__)


@dataclass
class Experiment:
    config: PipelineBenchConfig
    tool_name: str

    def run(self) -> None:
        system = self.config.get_ci_system(self.tool_name)
        if not system.enabled:
            raise RuntimeError(f"{self.tool_name} is disabled in config")

        provider = create_provider(self.config, system)
        prometheus = PrometheusClient(
            self.config.monitoring.prometheus_url,
            step_seconds=self.config.monitoring.scrape_interval_seconds,
        )
        started_at = datetime.now(timezone.utc)
        experiment_id = make_experiment_id(self.tool_name, started_at)
        output_dir = self._resolve_output_dir(experiment_id)
        logs_dir = ensure_logs_dir(output_dir)
        results: list[BenchmarkResult] = []
        metadata = create_experiment_metadata(
            config=self.config,
            system=system,
            experiment_id=experiment_id,
            started_at=started_at,
            run_directory=output_dir,
        )
        write_metadata(metadata, output_dir / "metadata.json")

        provider.deploy()
        provider.wait_until_ready()

        for warmup_id in range(1, self.config.experiment.warmup_runs + 1):
            LOGGER.info("Starting warmup run %s for %s", warmup_id, self.tool_name)
            self._run_once(provider, prometheus, self._metrics_namespaces(), logs_dir, -warmup_id, measured=False)

        for run_id in range(1, self.config.experiment.runs_per_tool + 1):
            LOGGER.info("Starting measured run %s for %s", run_id, self.tool_name)
            result = self._run_once(provider, prometheus, self._metrics_namespaces(), logs_dir, run_id, measured=True)
            results.append(result)
            if self.config.experiment.cleanup_between_runs:
                delete_completed_benchmark_pods(system.namespace)

        if self.config.results.export_csv:
            export_csv(results, output_dir / "processed" / "results.csv")
            if self.config.results.latest_alias:
                export_csv(results, self.config.results.output_dir / "processed" / "results.csv")
        if self.config.results.export_json:
            export_json(results, output_dir / "raw" / "results.json")
            if self.config.results.latest_alias:
                export_json(results, self.config.results.output_dir / "raw" / "results.json")
        summary = summarize_results(results)
        export_summary_csv(summary, output_dir / "processed" / "summary.csv")
        export_summary_json(summary, output_dir / "processed" / "summary.json")
        if self.config.results.latest_alias:
            export_summary_csv(summary, self.config.results.output_dir / "processed" / "summary.csv")
            export_summary_json(summary, self.config.results.output_dir / "processed" / "summary.json")
        if self.config.results.latest_alias:
            write_metadata(metadata, self.config.results.output_dir / "metadata.json")
        if self.config.experiment.cleanup_between_tools:
            provider.cleanup()

        LOGGER.info("Benchmark finished. Results written under %s", output_dir)

    def _run_once(
        self,
        provider,
        prometheus: PrometheusClient,
        metrics_namespaces: list[str],
        logs_dir: Path,
        run_id: int,
        measured: bool,
    ) -> BenchmarkResult:
        start = utc_now()
        pipeline_status = "UNKNOWN"
        pipeline_id = ""
        error_message = ""
        log_label = f"warmup-{abs(run_id)}" if run_id < 0 else f"run-{run_id}"
        logs_path = logs_dir / f"{self.tool_name}-{log_label}.log"

        try:
            pipeline_id = provider.trigger_pipeline(run_id=run_id)
            pipeline_status = provider.wait_for_pipeline(pipeline_id)
            if self.config.results.export_logs:
                provider.collect_logs(pipeline_id, str(logs_path))
        except Exception as exc:
            error_message = str(exc)
            pipeline_status = "ERROR"
            logs_path.write_text(error_message, encoding="utf-8")
            LOGGER.exception("Run %s failed", run_id)

        end = utc_now()
        metrics = prometheus.collect_namespaces_metrics(namespaces=metrics_namespaces, start=start, end=end)
        duration = (end - start).total_seconds()

        result = BenchmarkResult(
            tool_name=self.tool_name,
            run_id=run_id,
            pipeline_status=pipeline_status,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            duration_seconds=duration,
            avg_cpu_usage=metrics.avg_cpu_usage,
            max_cpu_usage=metrics.max_cpu_usage,
            avg_memory_usage=metrics.avg_memory_usage,
            max_memory_usage=metrics.max_memory_usage,
            pod_restart_count=metrics.pod_restart_count,
            namespace=",".join(metrics_namespaces),
            logs_path=str(logs_path),
            error_message=error_message,
        )

        if measured:
            LOGGER.info("Run %s completed with status %s in %.2fs", run_id, pipeline_status, duration)
        return result

    def _resolve_output_dir(self, experiment_id: str) -> Path:
        if self.config.results.use_run_directories:
            return self.config.results.output_dir / "runs" / experiment_id
        return self.config.results.output_dir

    def _metrics_namespaces(self) -> list[str]:
        system = self.config.get_ci_system(self.tool_name)
        return system.metrics_namespaces or [system.namespace]
