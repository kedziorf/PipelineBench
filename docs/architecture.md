# Architecture

PipelineBench runs fully on a local PC using WSL2, Docker Desktop, kind, Kubernetes, and Prometheus. The benchmark cluster is a kind cluster named `pipelinebench-local`; it is separate from Docker Desktop's optional built-in Kubernetes cluster.

## Components

```text
PipelineBench runner
  -> local kind cluster
    -> pipelinebench-monitoring
    -> pipelinebench-gitea
    -> provider namespaces
```

Shared infrastructure:

- `pipelinebench-monitoring`: Prometheus, kube-state-metrics, node exporter, and metrics-server.
- `pipelinebench-gitea`: local source repository for the benchmark workload and provider pipeline files.

Measured providers:

- `pipelinebench-jenkins`
- `pipelinebench-tekton` plus `tekton-pipelines`
- `pipelinebench-concourse`
- `pipelinebench-gitea-actions`
- `pipelinebench-woodpecker`

CircleCI-compatible and GitLab-compatible local Job providers are intentionally excluded from the final architecture because they are compatibility-shaped local jobs rather than real self-hosted CI systems.

## Source Flow

The sample workload is seeded into local Gitea as `filip/sample-app`. Jenkins and Tekton fetch the local Gitea archive. Concourse uses the local Gitea Git URL as a Concourse `git` resource. Gitea Actions and Woodpecker react to commits in the same local repository.

Shared Gitea gives every provider the same source forge while keeping the benchmark local. Gitea itself is shared infrastructure and is excluded from provider metrics by default.

## Measurement Flow

For each run, PipelineBench:

1. Triggers the selected provider.
2. Waits for success, failure, or timeout.
3. Collects provider logs.
4. Queries Prometheus for CPU, memory, and restart metrics over the provider namespace window.
5. Writes raw and processed results under `results/runs/<timestamp>_<tool>/`.

The global run timeout is `experiment.timeout_seconds` in `experiment-runner/config.yaml`. Individual providers can override it with `ci_systems[].timeout_seconds`; Woodpecker uses a tighter default because broken webhook or agent state should fail quickly.

## Local Networking

The kind cluster config maps Jenkins and Prometheus to host ports:

- Jenkins NodePort `30080` -> `http://localhost:8080`
- Prometheus NodePort `30090` -> `http://localhost:9090`

Other UIs are usually reached with `kubectl port-forward`:

- Gitea service `gitea-http` in `pipelinebench-gitea`: local port `30082` to service port `3000`
- Grafana service in `pipelinebench-monitoring`: local port `30091` to service port `80`
- Concourse web service in `pipelinebench-concourse`: local port `30084` to service port `8080`
- Woodpecker server service in `pipelinebench-woodpecker`: local port `30086` to service port `8000`
