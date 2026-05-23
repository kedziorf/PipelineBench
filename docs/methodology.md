# Methodology

PipelineBench compares CI/CD tools by running the same deterministic workload multiple times under local Kubernetes.

## Sequential Execution

Tools are benchmarked one at a time:

1. Deploy monitoring.
2. Deploy shared local Gitea and seed the workload repository.
3. Deploy one CI/CD tool.
4. Run a warmup pipeline.
5. Run measured pipelines.
6. Export metrics and logs.
7. Clean benchmark resources.
8. Move to the next provider.

This avoids direct resource interference between tools and keeps namespace-level Prometheus queries easier to interpret.

## Run Count

The default config runs:

- 1 warmup run
- 5 measured runs

Warmup results are not exported as measured rows. They exist to absorb first-run setup costs and reveal installation or authentication problems before measured iterations start.

## Metric Scope

Prometheus queries are scoped to the configured provider namespace list. Shared Gitea is excluded by default because every provider uses it as the same local source forge.

Tekton is the main multi-namespace provider: controller metrics come from `tekton-pipelines`, while benchmark workload pods run in `pipelinebench-tekton`.

## Timeouts And Failure Handling

The runner waits for each triggered pipeline until it reaches success, failure, or the configured timeout. The global timeout is `experiment.timeout_seconds`; a provider can override it with `ci_systems[].timeout_seconds`.

Woodpecker uses a shorter provider timeout because webhook delivery, OAuth activation, or agent registration issues can otherwise look like a long-running benchmark rather than a broken setup.

## Reproducibility Notes

Local machine load can still influence results. Close heavy applications before running experiments and avoid changing Docker Desktop resource limits between runs.

Use `kubectl config current-context` to confirm the active context is `kind-pipelinebench-local`. Docker Desktop's Kubernetes tab may show a different cluster or no useful workload details; the kind node normally appears as a Docker container.
