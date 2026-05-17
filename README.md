# PipelineBench

PipelineBench is a local research framework for comparing CI/CD pipeline tools in a controlled Kubernetes environment. The first MVP benchmarks Jenkins only, with the project structured so additional providers can be added later.

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
- `results/processed/results.csv`
- `results/processed/summary.csv`
- `results/processed/summary.json`
- `results/raw/results.json`

Each run directory includes `metadata.json` with local tool versions and cluster context, plus run-specific logs. The top-level CSV, JSON, and metadata files are convenience aliases for the latest run.

## Current MVP Scope

Implemented:

- Local kind cluster scripts
- Monitoring install script for Prometheus, kube-state-metrics, and metrics-server
- Jenkins installation script using Helm
- Deterministic Python sample workload
- Jenkins pipeline definition
- Python experiment runner with provider abstraction
- Jenkins provider
- Prometheus metric client
- CSV, JSON, and log export

Not implemented yet:

- GitLab Runner provider
- GitHub Actions self-hosted runner provider
- CircleCI-compatible local runner
- Tekton provider
- Statistical analysis dashboards

See `docs/` for architecture, methodology, metrics, and experiment design notes.
