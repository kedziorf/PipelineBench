#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONFIG_FILE="$(mktemp)"

if kind get clusters | grep -qx "$CLUSTER_NAME"; then
  echo "kind cluster '$CLUSTER_NAME' already exists."
  exit 0
fi

cat >"$CONFIG_FILE" <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 8080
        protocol: TCP
      - containerPort: 30090
        hostPort: 9090
        protocol: TCP
YAML

kind create cluster --name "$CLUSTER_NAME" --config "$CONFIG_FILE"
kubectl cluster-info --context "kind-$CLUSTER_NAME"
rm -f "$CONFIG_FILE"

echo "Created kind cluster '$CLUSTER_NAME'."
