# Architecture

PipelineBench is organized as a local monorepo with four main layers:

1. Local infrastructure scripts create and delete a kind cluster.
2. Kubernetes and Helm assets install monitoring and CI/CD systems.
3. Workloads and pipeline definitions define the benchmark work each tool must run.
4. The Python experiment runner triggers pipelines, collects metrics, and exports results.

## Local Infrastructure

`scripts/create-cluster.sh` creates a kind cluster named `pipelinebench-local` by default. NodePorts expose:

- Jenkins at `http://localhost:8080`
- Prometheus at `http://localhost:9090`

## Monitoring

The MVP uses `kube-prometheus-stack` plus Metrics Server. Prometheus is the primary source for CPU, memory, and restart metrics. Grafana is installed for optional manual inspection.

## CI/CD Providers

Providers implement `CICDProvider` in `experiment-runner/pipelinebench/providers/base.py`.

Jenkins and Tekton are implemented in the MVP. Future providers should add a class implementing the same methods, then register it in `providers/__init__.py`.
