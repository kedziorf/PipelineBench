#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"
NAMESPACE="pipelinebench-concourse"

kubectl config use-context "$CONTEXT"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$NAMESPACE" app.kubernetes.io/name=pipelinebench-concourse pipelinebench.io/component=ci-system --overwrite

helm repo add concourse https://concourse-charts.storage.googleapis.com/ >/dev/null
helm repo update >/dev/null

cat > /tmp/pipelinebench-concourse-values.yaml <<'YAML'
concourse:
  web:
    externalUrl: http://localhost:30084
    auth:
      mainTeam:
        localUser: test
secrets:
  localUsers: test:test
web:
  service:
    type: NodePort
    atcNodePort: 30084
worker:
  replicas: 1
  baggageclaim:
    driver: overlay
persistence:
  enabled: false
postgresql:
  enabled: true
YAML

helm upgrade --install pipelinebench-concourse concourse/concourse \
  --namespace "$NAMESPACE" \
  --values /tmp/pipelinebench-concourse-values.yaml \
  --wait \
  --timeout 15m

echo "Concourse installed at http://localhost:30084."
