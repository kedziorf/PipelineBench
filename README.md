# PipelineBench

PipelineBench is a fully local research framework for comparing real self-hosted CI/CD systems in a controlled Kubernetes environment. The final thesis provider lineup is Jenkins, Tekton, Concourse, Gitea Actions, and Woodpecker CI.

The framework is designed for WSL2/Linux-compatible tooling and runs with Docker, kind, kubectl, Helm, Python, Prometheus, and a shared local Gitea forge. It does not use public cloud infrastructure, SaaS CI, or compatibility-only CI shims.

## Architecture

PipelineBench creates or uses a local kind cluster, installs monitoring, installs shared local Gitea, seeds a `filip/sample-app` repository, and benchmarks one CI/CD provider at a time.

Shared infrastructure:

- `pipelinebench-monitoring` for Prometheus and related metrics components.
- `pipelinebench-gitea` for the local source repository used by every provider.

Benchmarked provider namespaces:

- `pipelinebench-jenkins`
- `pipelinebench-tekton` plus the Tekton control plane in `tekton-pipelines`
- `pipelinebench-concourse`
- `pipelinebench-gitea-actions`
- `pipelinebench-woodpecker`

Gitea is shared source-control infrastructure, not a measured provider namespace by default. Provider metrics focus on the CI/CD runtime namespace so shared forge overhead does not distort comparisons.

## Quick Start

Run these commands from the repository root:

```bash
make check-tools
make create-cluster
make install-monitoring
make install-gitea
```

Then install and run providers sequentially:

```bash
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
```

`make run-jenkins` reads the Jenkins admin password from Kubernetes automatically when possible. If that fails, set:

```bash
export JENKINS_URL=http://localhost:8080
export JENKINS_USER=admin
export JENKINS_API_TOKEN=<jenkins-admin-password-or-api-token>
```

Woodpecker uses Gitea OAuth. The installer creates a local Gitea OAuth application, stores the server database on a persistent volume, and restarts the agent after the server rollout so the agent reconnects to the current server state. The runner can bootstrap a local browser-style OAuth session and activate the repository automatically.

## Local Web Interfaces

The kind cluster maps only selected NodePorts directly to the host. Jenkins and Prometheus should open directly after installation:

- Jenkins: `http://localhost:8080`
- Prometheus: `http://localhost:9090`

For the shared forge and other provider UIs, use manual port-forwards when you want to inspect them in a browser:

```bash
kubectl -n pipelinebench-gitea port-forward service/gitea-http 30082:3000
kubectl -n pipelinebench-monitoring port-forward service/pipelinebench-prometheus-grafana 30091:80
kubectl -n pipelinebench-concourse port-forward service/pipelinebench-concourse-web 30084:8080
kubectl -n pipelinebench-woodpecker port-forward service/woodpecker-server 30086:8000
```

Then open:

- Gitea: `http://localhost:30082` with `filip` / `pipelinebench-local-password`
- Grafana: `http://localhost:30091` with `admin` / `prom-operator` unless changed in Helm values
- Concourse: `http://localhost:30084` with `test` / `test`
- Woodpecker: `http://localhost:30086`, signing in through Gitea OAuth

Tekton has no web UI installed by default. Gitea Actions is inspected through the shared Gitea UI rather than a separate service.

## Requirements

Install these tools on your WSL2 Linux distribution:

- Docker with WSL2 integration enabled
- kind
- kubectl
- Helm
- Python 3.12+
- curl
- jq
- git

The `scripts/check-tools.sh` script verifies required tools and prints installation links when something is missing.

Docker Desktop's Kubernetes tab is not the source of truth for this project. PipelineBench uses a kind cluster, so Docker Desktop normally shows the kind node container in the Containers tab. Use `kubectl config current-context` and `kubectl get pods -A` to inspect the actual cluster.

## Results

Benchmark results are written to:

```text
results/runs/<timestamp>_<tool>/
```

Each run directory includes `metadata.json` with local tool versions and cluster context, `processed/` summaries, `raw/` JSON, and run-specific logs.

After running all five providers, generate a combined CSV and Markdown comparison with:

```bash
make compare-results
```

By default this compares the latest Jenkins, Tekton, Concourse, Gitea Actions, and Woodpecker summaries and writes artifacts under `results/runs/<timestamp>_comparison/processed/`. For a fixed thesis comparison, pass explicit run directories:

```bash
python3 scripts/compare-results.py   --run results/runs/<timestamp>_jenkins   --run results/runs/<timestamp>_tekton   --run results/runs/<timestamp>_concourse   --run results/runs/<timestamp>_gitea-actions   --run results/runs/<timestamp>_woodpecker
```

## Current Scope

Implemented or scaffolded:

- Local kind cluster scripts
- Monitoring install script for Prometheus, kube-state-metrics, and metrics-server
- Shared local Gitea forge and repository seeding
- Jenkins provider
- Tekton provider
- Concourse provider
- Gitea Actions provider
- Woodpecker provider
- Deterministic Python sample workload
- Provider-specific pipeline definitions
- Prometheus metric client
- CSV, JSON, log, and comparison export

Not included in the final comparison:

- CircleCI-compatible local Job execution
- GitLab CI-compatible local Job execution
- Public cloud CI/CD services

Useful docs:

- `docs/local-access.md` for browser URLs, credentials, and port-forward commands.
- `docs/architecture.md` for local cluster and namespace structure.
- `docs/experiment-design.md` for the final provider lineup and run procedure.
- `docs/metrics.md` for exported fields and Prometheus query scope.
- Provider notes in `docs/jenkins.md`, `docs/tekton.md`, `docs/concourse.md`, `docs/gitea-actions.md`, and `docs/woodpecker.md`.
