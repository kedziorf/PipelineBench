# Tekton Provider

Tekton is the second PipelineBench provider. It represents a Kubernetes-native pipeline engine and gives a useful contrast with Jenkins.

## Install

```bash
make install-tekton
```

The installer applies the upstream Tekton Pipelines release manifest, then applies PipelineBench resources in `pipelinebench-tekton`.

By default, the script uses:

```bash
TEKTON_PIPELINES_VERSION=v1.12.0
```

Override `TEKTON_RELEASE_URL` or `TEKTON_PIPELINES_VERSION` if a different release is needed.

## Run

```bash
make run-tekton
```

The Tekton provider creates one `PipelineRun` per benchmark run and waits for the `Succeeded` condition. Logs are collected with Kubernetes labels for the created `PipelineRun`.

## Workload Parity

The Tekton pipeline mirrors the Jenkins workload:

1. Python unit tests.
2. CPU benchmark task.
3. Memory benchmark task.
4. Docker build check, skipped when Docker is unavailable.
