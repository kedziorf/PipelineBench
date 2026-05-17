# Experiment Design

The intended full experiment compares multiple CI/CD systems using a fixed workload and local Kubernetes cluster.

## Current MVP

Implemented provider:

- Jenkins
- Tekton
- CircleCI-compatible local Kubernetes Job provider

Planned providers:

- GitLab Runner

## Local Run Procedure

```bash
make check-tools
make create-cluster
make install-monitoring
make install-jenkins
make run-jenkins
```

Tekton can be tested after monitoring is installed:

```bash
make install-tekton
make run-tekton
```

The local CircleCI-compatible provider can also be tested after monitoring is installed:

```bash
make install-circleci
make run-circleci
```

## Result Directories

Each benchmark execution writes to a unique directory:

```text
results/runs/<timestamp>_<tool>/
```

Inside each run directory:

- `metadata.json` records environment and tool versions.
- `processed/results.csv` stores measured run rows.
- `processed/summary.csv` and `processed/summary.json` store aggregate statistics.
- `raw/results.json` stores the same rows as JSON.
- `logs/` stores provider run logs.

The default configuration keeps outputs only inside timestamped run directories. Set `results.latest_alias: true` in `experiment-runner/config.yaml` only if you want top-level convenience copies for the latest run.

## Adding a Future Provider

1. Add Helm values or Kubernetes manifests under `kubernetes/ci-systems/<provider>/`.
2. Add provider-specific pipeline files under `pipelines/<provider>/`.
3. Implement `CICDProvider` in `experiment-runner/pipelinebench/providers/<provider>.py`.
4. Register the provider in `experiment-runner/pipelinebench/providers/__init__.py`.
5. Add the provider to `experiment-runner/config.yaml`.
6. Update docs with setup notes and known limitations.
