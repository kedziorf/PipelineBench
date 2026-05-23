#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${PIPELINEBENCH_CLUSTER_NAME:-pipelinebench-local}"
CONTEXT="kind-$CLUSTER_NAME"
NAMESPACE="pipelinebench-gitea"
GITEA_IMAGE="${PIPELINEBENCH_GITEA_IMAGE:-docker.io/gitea/gitea:1.24.6-rootless}"
ADMIN_USER="${PIPELINEBENCH_GITEA_USER:-filip}"
ADMIN_PASSWORD="${PIPELINEBENCH_GITEA_PASSWORD:-pipelinebench-local-password}"
ADMIN_EMAIL="${PIPELINEBENCH_GITEA_EMAIL:-filipkedzior@gmail.com}"
RUNNER_TOKEN="${PIPELINEBENCH_GITEA_ACTIONS_TOKEN:-pipelinebench-actions-token-000000000001}"

kubectl config use-context "$CONTEXT"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$NAMESPACE" \
  app.kubernetes.io/name=pipelinebench-gitea \
  pipelinebench.io/component=shared-forge \
  --overwrite

kubectl -n "$NAMESPACE" create secret generic pipelinebench-gitea-admin \
  --from-literal=username="$ADMIN_USER" \
  --from-literal=password="$ADMIN_PASSWORD" \
  --from-literal=email="$ADMIN_EMAIL" \
  --from-literal=runner-token="$RUNNER_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: gitea-data
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: Service
metadata:
  name: gitea-http
  namespace: $NAMESPACE
  labels:
    app.kubernetes.io/name: pipelinebench-gitea
spec:
  type: NodePort
  selector:
    app.kubernetes.io/name: pipelinebench-gitea
  ports:
    - name: http
      port: 3000
      targetPort: 3000
      nodePort: 30082
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipelinebench-gitea
  namespace: $NAMESPACE
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: pipelinebench-gitea
  template:
    metadata:
      labels:
        app.kubernetes.io/name: pipelinebench-gitea
    spec:
      securityContext:
        fsGroup: 1000
      initContainers:
        - name: fix-permissions
          image: docker.io/library/busybox:1.36
          command:
            - sh
            - -c
            - chown -R 1000:1000 /var/lib/gitea
          securityContext:
            runAsUser: 0
          volumeMounts:
            - name: data
              mountPath: /var/lib/gitea
      containers:
        - name: gitea
          image: $GITEA_IMAGE
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 3000
            - name: ssh
              containerPort: 2222
          env:
            - name: USER_UID
              value: "1000"
            - name: USER_GID
              value: "1000"
            - name: GITEA__server__SSH_PORT
              value: "2222"
            - name: GITEA__server__DOMAIN
              value: gitea-http.$NAMESPACE.svc.cluster.local
            - name: GITEA__server__ROOT_URL
              value: http://gitea-http.$NAMESPACE.svc.cluster.local:3000/
            - name: GITEA__server__SSH_DOMAIN
              value: gitea-http.$NAMESPACE.svc.cluster.local
            - name: GITEA__database__DB_TYPE
              value: sqlite3
            - name: GITEA__database__PATH
              value: /var/lib/gitea/gitea.db
            - name: GITEA__security__INSTALL_LOCK
              value: "true"
            - name: GITEA__security__SECRET_KEY
              value: pipelinebench-local-secret-key
            - name: GITEA__oauth2__JWT_SECRET
              value: pipelinebench-local-jwt-secret
            - name: GITEA__repository__ROOT
              value: /var/lib/gitea/git/repositories
            - name: GITEA__service__DISABLE_REGISTRATION
              value: "true"
            - name: GITEA__actions__ENABLED
              value: "true"
            - name: GITEA__webhook__ALLOWED_HOST_LIST
              value: external,loopback,private
            - name: GITEA_RUNNER_REGISTRATION_TOKEN
              valueFrom:
                secretKeyRef:
                  name: pipelinebench-gitea-admin
                  key: runner-token
          readinessProbe:
            httpGet:
              path: /api/healthz
              port: 3000
            initialDelaySeconds: 20
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 30
          volumeMounts:
            - name: data
              mountPath: /var/lib/gitea
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: gitea-data
YAML

kubectl -n "$NAMESPACE" rollout status deployment/pipelinebench-gitea --timeout=10m
POD="$(kubectl -n "$NAMESPACE" get pod -l app.kubernetes.io/name=pipelinebench-gitea -o jsonpath='{.items[0].metadata.name}')"

if ! kubectl -n "$NAMESPACE" exec "$POD" -- gitea admin user list --config /etc/gitea/app.ini | grep -qw "$ADMIN_USER"; then
  kubectl -n "$NAMESPACE" exec "$POD" -- gitea admin user create \
    --admin \
    --username "$ADMIN_USER" \
    --password "$ADMIN_PASSWORD" \
    --email "$ADMIN_EMAIL" \
    --must-change-password=false \
    --config /etc/gitea/app.ini
fi

echo "Gitea installed at http://localhost:30082."
echo "Admin user: $ADMIN_USER"
./scripts/seed-gitea-repo.sh
