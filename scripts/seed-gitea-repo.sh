#!/usr/bin/env bash
set -euo pipefail

GITEA_URL="${PIPELINEBENCH_GITEA_URL:-http://localhost:30082}"
GITEA_USER="${PIPELINEBENCH_GITEA_USER:-filip}"
GITEA_PASSWORD="${PIPELINEBENCH_GITEA_PASSWORD:-pipelinebench-local-password}"
REPO_NAME="${PIPELINEBENCH_GITEA_REPO:-sample-app}"
REPO_URL_AUTH="${GITEA_URL#http://}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PORT_FORWARD_PID=""
if ! curl -fsS "$GITEA_URL/api/healthz" >/dev/null 2>&1; then
  if [ "$GITEA_URL" = "http://localhost:30082" ]; then
    kubectl -n pipelinebench-gitea port-forward service/gitea-http 30082:3000 >/tmp/pipelinebench-gitea-port-forward.log 2>&1 &
    PORT_FORWARD_PID="$!"
    trap 'if [ -n "$PORT_FORWARD_PID" ]; then kill "$PORT_FORWARD_PID" 2>/dev/null || true; fi; rm -rf "$TMP_DIR"' EXIT
  fi
fi

for attempt in $(seq 1 60); do
  if curl -fsS "$GITEA_URL/api/healthz" >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    echo "Gitea did not become healthy at $GITEA_URL"
    exit 1
  fi
  sleep 2
done

if ! curl -fsS -u "$GITEA_USER:$GITEA_PASSWORD" "$GITEA_URL/api/v1/repos/$GITEA_USER/$REPO_NAME" >/dev/null 2>&1; then
  curl -fsS -u "$GITEA_USER:$GITEA_PASSWORD" \
    -H 'Content-Type: application/json' \
    -X POST "$GITEA_URL/api/v1/user/repos" \
    --data "{\"name\":\"$REPO_NAME\",\"private\":false,\"auto_init\":false}" >/dev/null
fi

mkdir -p "$TMP_DIR/repo"
cp -R workloads/sample-app/. "$TMP_DIR/repo/"
mkdir -p "$TMP_DIR/repo/.gitea/workflows" "$TMP_DIR/repo/ci/concourse"
cp pipelines/gitea-actions/workflows/pipelinebench.yml "$TMP_DIR/repo/.gitea/workflows/pipelinebench.yml"
cp pipelines/woodpecker/.woodpecker.yml "$TMP_DIR/repo/.woodpecker.yml"
cp pipelines/concourse/task.yml "$TMP_DIR/repo/ci/concourse/task.yml"

cd "$TMP_DIR/repo"
git init -b main >/dev/null
git config user.name "Filip Kedzior"
git config user.email "filipkedzior@gmail.com"
git add .
git commit -m "Seed PipelineBench sample app" >/dev/null
git remote add origin "http://$GITEA_USER:$GITEA_PASSWORD@$REPO_URL_AUTH/$GITEA_USER/$REPO_NAME.git"
git push --force origin main >/dev/null

echo "Seeded local Gitea repository: $GITEA_URL/$GITEA_USER/$REPO_NAME"
