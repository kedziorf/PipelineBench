# Metrics

PipelineBench exports these fields for each measured run:

- `tool_name`
- `run_id`
- `pipeline_status`
- `start_time`
- `end_time`
- `duration_seconds`
- `avg_cpu_usage`
- `max_cpu_usage`
- `avg_memory_usage`
- `max_memory_usage`
- `pod_restart_count`
- `namespace`
- `logs_path`
- `error_message`

Warmup runs are executed before measured runs but are not exported to `processed/results.csv` or `raw/results.json`.

## Summary Outputs

After each benchmark, PipelineBench writes aggregate summary files:

- `processed/summary.csv`
- `processed/summary.json`

The summary includes:

- total runs
- successful runs
- failed runs
- success rate
- mean, median, min, max, and standard deviation for duration
- mean average CPU usage
- peak max CPU usage
- mean average memory usage
- peak max memory usage
- total pod restarts

## Prometheus Queries

The runner queries namespace-level metrics over each pipeline run window:

- `container_cpu_usage_seconds_total`
- `container_memory_working_set_bytes`
- `kube_pod_container_status_restarts_total`

Metric availability depends on the installed monitoring chart and Kubernetes distribution. If a query returns no data, the runner exports `null` for that field and logs a warning.

CPU and memory are collected with Prometheus range queries from the recorded pipeline start time to end time. Restart counts use a windowed `increase(...)` query sized to the actual run duration.

Some providers use more than one namespace. Jenkins uses one namespace for controller and agents. Tekton uses `tekton-pipelines` for controllers and `pipelinebench-tekton` for benchmark `PipelineRun` pods, so the runner supports provider-specific `metrics_namespaces` and aggregates them into one row.

## Interpreting Shared Infrastructure

Shared Gitea is not included in provider metrics by default. This means Gitea Actions and Woodpecker measurements focus on their runner/server namespaces, while common source-control overhead is kept outside the comparison.

If a research question needs end-to-end forge overhead, add `pipelinebench-gitea` to a provider's `metrics_namespaces` explicitly and document that change in the result notes.
