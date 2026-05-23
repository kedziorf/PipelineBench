# Tekton Provider

Tekton represents the Kubernetes-native pipeline engine in the final PipelineBench lineup. It gives a contrast with controller-based Jenkins and with Git-forge-integrated systems such as Gitea Actions and Woodpecker.

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

## Source And Workload

The Tekton pipeline fetches the workload archive from the shared local Gitea repository. It mirrors the common workload shape:

1. Python unit tests.
2. CPU benchmark task.
3. Memory benchmark task.
4. Docker build check, skipped when Docker is unavailable.

## Local UI

No Tekton Dashboard is installed by default. Inspect Tekton through Kubernetes commands, for example:

```bash
kubectl -n pipelinebench-tekton get pipelineruns
kubectl -n pipelinebench-tekton logs -l pipelinebench.io/experiment=sample-app
```
