#!/usr/bin/env bash
set -euo pipefail

TOOL="${1:-jenkins}"

case "$TOOL" in
  jenkins|tekton|concourse|gitea-actions|woodpecker) ;;
  *)
    echo "Supported providers: jenkins, tekton, concourse, gitea-actions, woodpecker"
    exit 1
    ;;
esac

if [ "$TOOL" = "jenkins" ]; then
  export JENKINS_URL="${JENKINS_URL:-http://localhost:8080}"
  export JENKINS_USER="${JENKINS_USER:-admin}"
  if [ -z "${JENKINS_API_TOKEN:-}" ] && command -v kubectl >/dev/null 2>&1; then
    JENKINS_API_TOKEN="$(kubectl -n pipelinebench-jenkins get secret pipelinebench-jenkins -o jsonpath='{.data.jenkins-admin-password}' 2>/dev/null | base64 --decode || true)"
    export JENKINS_API_TOKEN
  fi

  if [ -z "${JENKINS_API_TOKEN:-}" ]; then
    echo "JENKINS_API_TOKEN is not set and the Jenkins admin password could not be read from Kubernetes."
    echo "Set JENKINS_API_TOKEN, then rerun make run-jenkins."
    exit 1
  fi
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r experiment-runner/requirements.txt
python experiment-runner/main.py run --config experiment-runner/config.yaml --tool "$TOOL"
