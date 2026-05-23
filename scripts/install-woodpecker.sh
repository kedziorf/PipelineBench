#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"
NAMESPACE="pipelinebench-woodpecker"
GITEA_URL="${PIPELINEBENCH_GITEA_INTERNAL_URL:-http://gitea-http.pipelinebench-gitea.svc.cluster.local:3000}"
GITEA_EXTERNAL_URL="${PIPELINEBENCH_GITEA_URL:-http://localhost:30082}"
GITEA_USER="${PIPELINEBENCH_GITEA_USER:-filip}"
GITEA_PASSWORD="${PIPELINEBENCH_GITEA_PASSWORD:-pipelinebench-local-password}"
WOODPECKER_AGENT_SECRET="${PIPELINEBENCH_WOODPECKER_AGENT_SECRET:-pipelinebench-woodpecker-agent-secret}"
WOODPECKER_WEBHOOK_URL="${PIPELINEBENCH_WOODPECKER_WEBHOOK_URL:-http://woodpecker-server.$NAMESPACE.svc.cluster.local:8000}"
WOODPECKER_CLIENT="${PIPELINEBENCH_WOODPECKER_GITEA_CLIENT:-pipelinebench-woodpecker}"
WOODPECKER_SECRET="${PIPELINEBENCH_WOODPECKER_GITEA_SECRET:-pipelinebench-woodpecker-secret}"
WOODPECKER_SERVER_IMAGE="${PIPELINEBENCH_WOODPECKER_SERVER_IMAGE:-docker.io/woodpeckerci/woodpecker-server:v3}"
WOODPECKER_AGENT_IMAGE="${PIPELINEBENCH_WOODPECKER_AGENT_IMAGE:-docker.io/woodpeckerci/woodpecker-agent:v3}"

kubectl config use-context "$CONTEXT"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$NAMESPACE" app.kubernetes.io/name=pipelinebench-woodpecker pipelinebench.io/component=ci-system --overwrite

GITEA_PORT_FORWARD_PID=""
if ! curl -fsS "$GITEA_EXTERNAL_URL/api/healthz" >/dev/null 2>&1; then
  echo "Opening temporary port-forward to local Gitea at $GITEA_EXTERNAL_URL ..."
  kubectl -n pipelinebench-gitea port-forward service/gitea-http 30082:3000 >/tmp/pipelinebench-gitea-woodpecker-port-forward.log 2>&1 &
  GITEA_PORT_FORWARD_PID="$!"
  trap 'if [ -n "${GITEA_PORT_FORWARD_PID:-}" ]; then kill "$GITEA_PORT_FORWARD_PID" 2>/dev/null || true; fi' EXIT
  for _ in {1..30}; do
    if curl -fsS "$GITEA_EXTERNAL_URL/api/healthz" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

# Best-effort creation of the Gitea OAuth application used by Woodpecker.
# If the API shape changes, callers can still provide PIPELINEBENCH_WOODPECKER_GITEA_CLIENT/SECRET.
OAUTH_RESPONSE="$(curl -fsS -u "$GITEA_USER:$GITEA_PASSWORD" \
  -H 'Content-Type: application/json' \
  -X POST "$GITEA_EXTERNAL_URL/api/v1/user/applications/oauth2" \
  --data "{\"name\":\"pipelinebench-woodpecker-$(date +%s)\",\"redirect_uris\":[\"http://localhost:30086/authorize\"],\"confidential_client\":true,\"skip_secondary_authorization\":true}" 2>/dev/null || true)"
if [ -n "$OAUTH_RESPONSE" ] && command -v jq >/dev/null 2>&1; then
  CREATED_CLIENT="$(printf '%s' "$OAUTH_RESPONSE" | jq -r '.client_id // empty')"
  CREATED_SECRET="$(printf '%s' "$OAUTH_RESPONSE" | jq -r '.client_secret // empty')"
  if [ -n "$CREATED_CLIENT" ] && [ -n "$CREATED_SECRET" ]; then
    WOODPECKER_CLIENT="$CREATED_CLIENT"
    WOODPECKER_SECRET="$CREATED_SECRET"
  fi
fi

kubectl -n "$NAMESPACE" create secret generic pipelinebench-woodpecker \
  --from-literal=agent-secret="$WOODPECKER_AGENT_SECRET" \
  --from-literal=gitea-client="$WOODPECKER_CLIENT" \
  --from-literal=gitea-secret="$WOODPECKER_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: woodpecker-data
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pipelinebench-woodpecker-agent
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pipelinebench-woodpecker-agent
  namespace: $NAMESPACE
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/exec", "services", "persistentvolumeclaims", "configmaps", "secrets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pipelinebench-woodpecker-agent
  namespace: $NAMESPACE
subjects:
  - kind: ServiceAccount
    name: pipelinebench-woodpecker-agent
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pipelinebench-woodpecker-agent
---
apiVersion: v1
kind: Service
metadata:
  name: woodpecker-server
  namespace: $NAMESPACE
spec:
  type: NodePort
  selector:
    app.kubernetes.io/name: pipelinebench-woodpecker-server
  ports:
    - name: http
      port: 8000
      targetPort: 8000
      nodePort: 30086
    - name: grpc
      port: 9000
      targetPort: 9000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipelinebench-woodpecker-server
  namespace: $NAMESPACE
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: pipelinebench-woodpecker-server
  template:
    metadata:
      labels:
        app.kubernetes.io/name: pipelinebench-woodpecker-server
    spec:
      containers:
        - name: server
          image: $WOODPECKER_SERVER_IMAGE
          ports:
            - name: http
              containerPort: 8000
            - name: grpc
              containerPort: 9000
          env:
            - name: WOODPECKER_OPEN
              value: "true"
            - name: WOODPECKER_ADMIN
              value: filip
            - name: WOODPECKER_HOST
              value: http://localhost:30086
            - name: WOODPECKER_GITEA
              value: "true"
            - name: WOODPECKER_GITEA_URL
              value: $GITEA_URL
            - name: WOODPECKER_EXPERT_WEBHOOK_HOST
              value: $WOODPECKER_WEBHOOK_URL
            - name: WOODPECKER_EXPERT_FORGE_OAUTH_HOST
              value: $GITEA_EXTERNAL_URL
            - name: WOODPECKER_GITEA_CLIENT
              valueFrom:
                secretKeyRef:
                  name: pipelinebench-woodpecker
                  key: gitea-client
            - name: WOODPECKER_GITEA_SECRET
              valueFrom:
                secretKeyRef:
                  name: pipelinebench-woodpecker
                  key: gitea-secret
            - name: WOODPECKER_AGENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: pipelinebench-woodpecker
                  key: agent-secret
          volumeMounts:
            - name: data
              mountPath: /var/lib/woodpecker
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: woodpecker-data
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipelinebench-woodpecker-agent
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: pipelinebench-woodpecker-agent
  template:
    metadata:
      labels:
        app.kubernetes.io/name: pipelinebench-woodpecker-agent
    spec:
      serviceAccountName: pipelinebench-woodpecker-agent
      containers:
        - name: agent
          image: $WOODPECKER_AGENT_IMAGE
          env:
            - name: WOODPECKER_SERVER
              value: woodpecker-server.$NAMESPACE.svc.cluster.local:9000
            - name: WOODPECKER_AGENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: pipelinebench-woodpecker
                  key: agent-secret
            - name: WOODPECKER_BACKEND
              value: kubernetes
            - name: WOODPECKER_BACKEND_K8S_NAMESPACE
              value: $NAMESPACE
            - name: WOODPECKER_BACKEND_K8S_STORAGE_RWX
              value: "false"
            - name: WOODPECKER_BACKEND_K8S_VOLUME_SIZE
              value: 1Gi
YAML

kubectl -n "$NAMESPACE" rollout status deployment/pipelinebench-woodpecker-server --timeout=10m
kubectl -n "$NAMESPACE" rollout restart deployment/pipelinebench-woodpecker-agent
kubectl -n "$NAMESPACE" rollout status deployment/pipelinebench-woodpecker-agent --timeout=10m
echo "Woodpecker installed at http://localhost:30086."
echo "Create a Gitea OAuth app for Woodpecker if not already configured, then set WOODPECKER_TOKEN for API-based triggering."
