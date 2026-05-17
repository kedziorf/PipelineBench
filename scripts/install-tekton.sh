#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"
TEKTON_PIPELINES_VERSION="${TEKTON_PIPELINES_VERSION:-v1.12.0}"
TEKTON_RELEASE_URL="${TEKTON_RELEASE_URL:-https://infra.tekton.dev/tekton-releases/pipeline/previous/${TEKTON_PIPELINES_VERSION}/release.yaml}"

kubectl config use-context "$CONTEXT"

echo "Installing Tekton Pipelines from ${TEKTON_RELEASE_URL}"
kubectl apply --filename "$TEKTON_RELEASE_URL"
kubectl -n tekton-pipelines wait deployment --all --for=condition=Available --timeout=10m

kubectl apply -f kubernetes/namespaces/tekton.yaml
kubectl apply -f kubernetes/ci-systems/tekton/rbac.yaml
kubectl apply -f kubernetes/ci-systems/tekton/sample-workload-configmap.yaml
kubectl apply -f kubernetes/ci-systems/tekton/pipeline.yaml

echo "Tekton installed and PipelineBench Tekton resources applied."
