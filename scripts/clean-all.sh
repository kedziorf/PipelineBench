#!/usr/bin/env bash
set -euo pipefail

kubectl delete namespace pipelinebench-jenkins --ignore-not-found=true
kubectl delete namespace pipelinebench-tekton --ignore-not-found=true
kubectl delete namespace pipelinebench-circleci --ignore-not-found=true
kubectl delete namespace pipelinebench-monitoring --ignore-not-found=true
kubectl delete namespace tekton-pipelines --ignore-not-found=true
echo "Deleted PipelineBench namespaces. Use make delete-cluster to remove the kind cluster."
