# Experiment Design

The final experiment compares five real CI/CD systems using one local Kubernetes cluster, one deterministic workload, one shared local source repository, and one Prometheus monitoring stack.

## Provider Lineup

Measured providers:

- Jenkins
- Tekton
- Concourse
- Gitea Actions
- Woodpecker CI

Removed from the final comparison:

- CircleCI-compatible local Kubernetes Job provider
- GitLab CI-compatible local Kubernetes Job provider

Those compatible providers were useful exploration artifacts, but they do not run the real hosted or self-hosted CI system control plane. The final comparison includes only real local systems.

## Shared Local Source Repository

All providers consume the same repository from local Gitea:

```text
pipelinebench-gitea
  filip/sample-app
```

Gitea is shared source-control infrastructure. It is not included in provider metrics by default. This keeps provider measurements focused on each CI/CD runtime rather than the shared forge.

## Local Run Procedure

```bash
make check-tools
make create-cluster
make install-monitoring
make install-gitea

make install-jenkins
make run-jenkins

make install-tekton
make run-tekton

make install-concourse
make run-concourse

make install-gitea-actions
make run-gitea-actions

make install-woodpecker
make run-woodpecker

make compare-results
```

The default experiment runs one warmup and five measured runs per provider. Warmup runs validate that the provider and workload are ready, but they are not exported as measured rows.

## Timeouts

The global per-run wait timeout is configured as:

```yaml
experiment:
  timeout_seconds: 1800
```

Providers can override this with `ci_systems[].timeout_seconds`. Woodpecker defaults to `300` seconds per warmup or measured run so webhook, OAuth, or agent registration problems fail quickly instead of blocking for the global timeout.

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

## Fixed Comparison

For a reproducible thesis table, pass explicit run directories to the comparison script instead of relying on the latest-run lookup:

```bash
python3 scripts/compare-results.py   --run results/runs/<timestamp>_jenkins   --run results/runs/<timestamp>_tekton   --run results/runs/<timestamp>_concourse   --run results/runs/<timestamp>_gitea-actions   --run results/runs/<timestamp>_woodpecker
```

The comparison output is written under `results/runs/<timestamp>_comparison/processed/` as CSV and Markdown.

## Adding A Future Provider

1. Add Helm values, Kubernetes manifests, or a dedicated install script.
2. Add provider-specific pipeline files under `pipelines/<provider>/`.
3. Implement `CICDProvider` in `experiment-runner/pipelinebench/providers/<provider>.py`.
4. Register the provider in `experiment-runner/pipelinebench/providers/__init__.py`.
5. Add the provider to `experiment-runner/config.yaml`.
6. Update docs with setup notes, local access details, timeout behavior, and known limitations.

Future providers should be real self-hosted/open-source/local systems, not compatibility-shaped local emulations of SaaS CI syntax.
