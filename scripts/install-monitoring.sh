#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"

kubectl config use-context "$CONTEXT"
kubectl apply -f kubernetes/namespaces/monitoring.yaml

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null
helm repo update >/dev/null

helm upgrade --install pipelinebench-prometheus prometheus-community/kube-prometheus-stack \
  --namespace pipelinebench-monitoring \
  --values helm/values/prometheus-values.yaml \
  --wait \
  --timeout 10m

helm upgrade --install metrics-server metrics-server/metrics-server \
  --namespace kube-system \
  --set args="{--kubelet-insecure-tls,--kubelet-preferred-address-types=InternalIP,Hostname,ExternalIP}" \
  --wait \
  --timeout 5m

echo "Monitoring stack installed."
echo "Prometheus is exposed through NodePort 30090. Access it at http://localhost:9090."
