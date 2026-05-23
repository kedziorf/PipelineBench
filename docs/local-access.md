# Local Access

PipelineBench runs on a kind cluster named `pipelinebench-local`. Docker Desktop's Kubernetes tab is not the main view for this project; the kind node normally appears as a Docker container. Use `kubectl` against `kind-pipelinebench-local` for accurate cluster state.

## Check The Cluster

```bash
kubectl config current-context
kubectl get namespaces
kubectl get pods -A
```

The current context should be:

```text
kind-pipelinebench-local
```

## Web Interfaces

| Service | URL | Access | Credentials |
| --- | --- | --- | --- |
| Jenkins | `http://localhost:8080` | Direct kind host port mapping | `admin` plus the Kubernetes secret value |
| Prometheus | `http://localhost:9090` | Direct kind host port mapping | None |
| Grafana | `http://localhost:30091` | Manual port-forward | `admin` / `prom-operator` unless changed in Helm values |
| Gitea | `http://localhost:30082` | Manual port-forward | `filip` / `pipelinebench-local-password` |
| Concourse | `http://localhost:30084` | Manual port-forward | `test` / `test` |
| Woodpecker | `http://localhost:30086` | Manual port-forward | Gitea OAuth |
| Tekton | None by default | `kubectl` only | Not applicable |
| Gitea Actions | Inside Gitea | Gitea UI | Gitea credentials |

## Port-Forward Commands

```bash
kubectl -n pipelinebench-gitea port-forward service/gitea-http 30082:3000
kubectl -n pipelinebench-monitoring port-forward service/pipelinebench-prometheus-grafana 30091:80
kubectl -n pipelinebench-concourse port-forward service/pipelinebench-concourse-web 30084:8080
kubectl -n pipelinebench-woodpecker port-forward service/woodpecker-server 30086:8000
```

Run each port-forward in its own terminal and stop it with `Ctrl+C` when finished.

## Jenkins Password

```bash
kubectl -n pipelinebench-jenkins get secret pipelinebench-jenkins   -o jsonpath='{.data.jenkins-admin-password}' | base64 --decode
```

## Notes

The benchmark providers may open temporary port-forwards while a run is active. Those are process-local helpers for the runner; for manual browsing, start your own port-forward so the browser session remains stable.
