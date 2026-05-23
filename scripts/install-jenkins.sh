#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"

kubectl config use-context "$CONTEXT"
kubectl apply -f kubernetes/namespaces/jenkins.yaml
kubectl apply -f kubernetes/ci-systems/jenkins/rbac.yaml
kubectl apply -f kubernetes/ci-systems/jenkins/jenkinsfile-configmap.yaml

helm repo add jenkins https://charts.jenkins.io >/dev/null
helm repo update >/dev/null

helm upgrade --install pipelinebench-jenkins jenkins/jenkins \
  --namespace pipelinebench-jenkins \
  --values helm/values/jenkins-values.yaml \
  --wait \
  --timeout 15m

echo "Jenkins installed."
echo "Jenkins is exposed through NodePort 30080. Access it at http://localhost:8080."
echo "Initial admin password:"
kubectl -n pipelinebench-jenkins get secret pipelinebench-jenkins -o jsonpath='{.data.jenkins-admin-password}' | base64 --decode
echo
