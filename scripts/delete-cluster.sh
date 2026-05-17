#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"

if kind get clusters | grep -qx "$CLUSTER_NAME"; then
  kind delete cluster --name "$CLUSTER_NAME"
  echo "Deleted kind cluster '$CLUSTER_NAME'."
else
  echo "kind cluster '$CLUSTER_NAME' does not exist."
fi
