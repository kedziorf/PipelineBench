# Experiment Design

The intended full experiment compares multiple CI/CD systems using a fixed workload and local Kubernetes cluster.

## Current MVP

Implemented provider:

- Jenkins

Planned providers:

- GitLab Runner
- GitHub Actions self-hosted runner
- CircleCI-compatible local runner or placeholder
- Tekton

## Local Run Procedure

```bash
make check-tools
make create-cluster
make install-monitoring
make install-jenkins
make run-jenkins
```

## Result Directories

Each benchmark execution writes to a unique directory:

```text
results/runs/<timestamp>_<tool>/
```

Inside each run directory:

- `metadata.json` records environment and tool versions.
- `processed/results.csv` stores measured run rows.
- `raw/results.json` stores the same rows as JSON.
- `logs/` stores Jenkins console logs.

For convenience, the latest CSV, JSON, and metadata are also copied to `results/processed/results.csv`, `results/raw/results.json`, and `results/metadata.json`.

## Adding a Future Provider

1. Add Helm values or Kubernetes manifests under `kubernetes/ci-systems/<provider>/`.
2. Add provider-specific pipeline files under `pipelines/<provider>/`.
3. Implement `CICDProvider` in `experiment-runner/pipelinebench/providers/<provider>.py`.
4. Register the provider in `experiment-runner/pipelinebench/providers/__init__.py`.
5. Add the provider to `experiment-runner/config.yaml`.
6. Update docs with setup notes and known limitations.
