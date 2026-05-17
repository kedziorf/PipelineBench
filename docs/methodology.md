# Methodology

PipelineBench compares CI/CD tools by running the same workload multiple times under local Kubernetes.

## Sequential Execution

Tools are benchmarked one at a time:

1. Deploy monitoring.
2. Deploy one CI/CD tool.
3. Run a warmup pipeline.
4. Run measured pipelines.
5. Export metrics and logs.
6. Clean benchmark resources.
7. Remove the tool before testing the next one.

This avoids direct resource interference between tools and keeps namespace-level Prometheus queries easier to interpret.

## MVP Run Count

The default config runs:

- 1 warmup run
- 5 measured runs

Warmup results are not exported.

## Reproducibility Notes

Local machine load can still influence results. Close heavy applications before running experiments and avoid changing Docker Desktop resource limits between runs.
