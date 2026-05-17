# PipelineBench Project Goal

PipelineBench supports a master's thesis experiment comparing selected CI/CD pipeline tools under repeatable local Kubernetes conditions.

The research goal is to measure pipeline execution behavior across tools while controlling for workload, cluster, monitoring stack, and execution order.

## Intended Tool Coverage

The long-term comparison may include:

- Jenkins
- GitLab Runner
- GitHub Actions self-hosted runner
- CircleCI-compatible local runner or placeholder
- Tekton

The MVP implements Jenkins only.

## Experimental Principles

- All infrastructure runs locally.
- No public cloud providers are used.
- CI/CD systems run sequentially.
- Every tool executes the same workload.
- Results are exported in machine-readable CSV and JSON formats.
- Cleanup happens between tools to reduce measurement interference.
