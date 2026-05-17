#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"
NAMESPACE="pipelinebench-circleci"

kubectl config use-context "$CONTEXT"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$NAMESPACE" \
  app.kubernetes.io/name=pipelinebench-circleci \
  pipelinebench.io/component=ci-system \
  --overwrite

kubectl -n "$NAMESPACE" create configmap pipelinebench-sample-workload \
  --from-file=requirements.txt=workloads/sample-app/requirements.txt \
  --from-file=app.py=workloads/sample-app/src/app.py \
  --from-file=test_app.py=workloads/sample-app/tests/test_app.py \
  --from-file=cpu_task.py=workloads/sample-app/benchmark/cpu_task.py \
  --from-file=memory_task.py=workloads/sample-app/benchmark/memory_task.py \
  --from-file=Dockerfile=workloads/sample-app/Dockerfile \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NAMESPACE" create configmap pipelinebench-circleci-config \
  --from-file=config.yml=pipelines/circleci/config.yml \
  --dry-run=client -o yaml | kubectl apply -f -

echo "CircleCI-compatible local Kubernetes resources applied."
