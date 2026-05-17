# CircleCI-Compatible Local Provider

PipelineBench does not use CircleCI Cloud, the CircleCI API, or public cloud resources.

The provider is a local compatibility implementation for benchmarking a CircleCI-shaped pipeline in kind. `pipelines/circleci/config.yml` records the CircleCI 2.1 workflow shape, and the experiment runner creates one Kubernetes `Job` per warmup or measured run in `pipelinebench-circleci`.

## Why Not Official CircleCI Local Execution

The official CircleCI local execution path is Docker-oriented and runs individual jobs locally with Docker, with workflow-level limitations documented by CircleCI: <https://circleci.com/docs/how-to-use-the-circleci-local-cli/>. It is not a Kubernetes controller running inside kind. That makes it difficult to compare fairly with Jenkins and Tekton through Kubernetes namespace metrics.

For this thesis benchmark, the closest honest local design is therefore:

- keep a CircleCI-style config file as the pipeline definition;
- execute the same workload stages in a Kubernetes `Job`;
- collect Prometheus metrics from `pipelinebench-circleci`;
- document that this measures a local CircleCI-compatible execution model, not CircleCI Cloud.

## Install

```bash
make install-circleci
```

The installer creates `pipelinebench-circleci` and stores the sample workload plus CircleCI config in ConfigMaps.

## Run

```bash
make run-circleci
```

The provider creates one Kubernetes `Job` per benchmark run and waits for the Job to complete. Logs are collected with `kubectl logs job/<job-name>`.

Each Job includes a short observation hold after the workload commands. This keeps the pod alive long enough for Prometheus scrapes in the local kind cluster.

## Workload Parity

The local CircleCI-compatible job mirrors Jenkins and Tekton:

1. Prepare source.
2. Install Python dependencies.
3. Run Python unit tests.
4. Run CPU benchmark.
5. Run memory benchmark.
6. Run Docker build check, skipped when Docker is unavailable.
