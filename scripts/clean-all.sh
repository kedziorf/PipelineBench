#!/usr/bin/env bash
set -euo pipefail

kubectl delete namespace pipelinebench-jenkins --ignore-not-found=true
kubectl delete namespace pipelinebench-tekton --ignore-not-found=true
kubectl delete namespace pipelinebench-concourse --ignore-not-found=true
kubectl delete namespace pipelinebench-gitea-actions --ignore-not-found=true
kubectl delete namespace pipelinebench-woodpecker --ignore-not-found=true
kubectl delete namespace pipelinebench-gitea --ignore-not-found=true
kubectl delete namespace pipelinebench-monitoring --ignore-not-found=true
kubectl delete namespace tekton-pipelines --ignore-not-found=true
kubectl delete namespace tekton-pipelines-resolvers --ignore-not-found=true
echo "Deleted PipelineBench namespaces. Use make delete-cluster to remove the kind cluster."
