# Tekton Pipeline

Tekton uses Kubernetes-native `Pipeline`, `Task`, and `PipelineRun` resources.

The MVP Tekton pipeline mirrors the Jenkins workload:

1. Run Python unit tests.
2. Run CPU benchmark task.
3. Run memory benchmark task.
4. Check whether Docker is available and skip image build when it is not.

The pipeline is installed from `kubernetes/ci-systems/tekton/pipeline.yaml`.
