#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"
NAMESPACE="pipelinebench-gitea-actions"
GITEA_INTERNAL_URL="${PIPELINEBENCH_GITEA_INTERNAL_URL:-http://gitea-http.pipelinebench-gitea.svc.cluster.local:3000}"
RUNNER_TOKEN="${PIPELINEBENCH_GITEA_ACTIONS_TOKEN:-pipelinebench-actions-token-000000000001}"
ACT_RUNNER_IMAGE="${PIPELINEBENCH_ACT_RUNNER_IMAGE:-docker.io/gitea/act_runner:latest}"
DIND_IMAGE="${PIPELINEBENCH_DIND_IMAGE:-docker.io/library/docker:27-dind}"

kubectl config use-context "$CONTEXT"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$NAMESPACE" app.kubernetes.io/name=pipelinebench-gitea-actions pipelinebench.io/component=ci-system --overwrite

kubectl -n "$NAMESPACE" create secret generic pipelinebench-gitea-actions-runner \
  --from-literal=token="$RUNNER_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipelinebench-gitea-actions-runner
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: pipelinebench-gitea-actions-runner
  template:
    metadata:
      labels:
        app.kubernetes.io/name: pipelinebench-gitea-actions-runner
    spec:
      containers:
        - name: dind
          image: $DIND_IMAGE
          securityContext:
            privileged: true
          env:
            - name: DOCKER_TLS_CERTDIR
              value: ""
          command:
            - dockerd-entrypoint.sh
            - --host=tcp://0.0.0.0:2375
            - --tls=false
        - name: runner
          image: $ACT_RUNNER_IMAGE
          env:
            - name: DOCKER_HOST
              value: tcp://localhost:2375
            - name: GITEA_INSTANCE_URL
              value: $GITEA_INTERNAL_URL
            - name: GITEA_RUNNER_REGISTRATION_TOKEN
              valueFrom:
                secretKeyRef:
                  name: pipelinebench-gitea-actions-runner
                  key: token
          command:
            - /bin/sh
            - -ceu
            - |
              sleep 10
              if [ ! -f .runner ]; then
                act_runner register --no-interactive \
                  --instance "\$GITEA_INSTANCE_URL" \
                  --token "\$GITEA_RUNNER_REGISTRATION_TOKEN" \
                  --name pipelinebench-gitea-actions-runner \
                  --labels ubuntu-latest:docker://python:3.12-slim,ubuntu-22.04:docker://python:3.12-slim
              fi
              exec act_runner daemon
YAML

kubectl -n "$NAMESPACE" rollout status deployment/pipelinebench-gitea-actions-runner --timeout=10m
echo "Gitea Actions runner installed."
