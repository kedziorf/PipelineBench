# PipelineBench

PipelineBench is a local research framework for comparing CI/CD pipeline tools in a controlled Kubernetes environment. The current MVP benchmarks Jenkins, Tekton, and a local CircleCI-compatible Kubernetes execution model.

The framework is designed for WSL2/Linux-compatible tooling and runs fully locally with Docker, kind, kubectl, Helm, Python, and Prometheus. It does not use public cloud infrastructure.

## Why Sequential Execution

CI/CD systems are deployed and measured one at a time. After each tool is benchmarked, its namespace and temporary resources are removed before the next tool is installed. This reduces resource interference and makes CPU, memory, restart, and duration measurements easier to compare.

## Quick Start

Run these commands from the repository root:

```bash
make check-tools
make create-cluster
make install-monitoring
make install-jenkins
make run-jenkins
```

`make run-jenkins` runs the Jenkins benchmark using the Python experiment runner.
The script reads the Jenkins admin password from Kubernetes automatically when possible. If that fails, set:

```bash
export JENKINS_URL=http://localhost:8080
export JENKINS_USER=admin
export JENKINS_API_TOKEN=<jenkins-admin-password-or-api-token>
```

To run Tekton after the cluster and monitoring stack are ready:

```bash
make install-tekton
make run-tekton
```

To run the local CircleCI-compatible provider after the cluster and monitoring stack are ready:

```bash
make install-circleci
make run-circleci
```

## Requirements

Install these tools on your WSL2 Linux distribution:

- Docker with WSL2 integration enabled
- kind
- kubectl
- Helm
- Python 3.12+
- curl
- jq

The `scripts/check-tools.sh` script verifies required tools and prints installation links when something is missing.

## Results

Benchmark results are written to:

- `results/runs/<timestamp>_<tool>/`

Each run directory includes `metadata.json` with local tool versions and cluster context, `processed/` summaries, `raw/` JSON, and run-specific logs.

## Current MVP Scope

Implemented:

- Local kind cluster scripts
- Monitoring install script for Prometheus, kube-state-metrics, and metrics-server
- Jenkins installation script using Helm
- Tekton installation script using upstream Tekton Pipelines manifests
- CircleCI-compatible local Kubernetes Job provider
- Deterministic Python sample workload
- Jenkins pipeline definition
- Tekton pipeline definition
- CircleCI pipeline definition
- Python experiment runner with provider abstraction
- Jenkins provider
- Tekton provider
- CircleCI provider
- Prometheus metric client
- CSV, JSON, and log export

Not implemented yet:

- GitLab Runner provider
- Statistical analysis dashboards

See `docs/` for architecture, methodology, metrics, Tekton, CircleCI, and experiment design notes.
