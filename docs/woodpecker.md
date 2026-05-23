# Woodpecker Provider

The Woodpecker provider deploys a local Woodpecker server and agent in `pipelinebench-woodpecker`. The agent is configured for the Kubernetes backend so pipeline steps run as Kubernetes pods in the Woodpecker namespace.

## Source And Authentication

Woodpecker is connected to the shared local Gitea forge. The installer creates a local Gitea OAuth application and configures Woodpecker with:

- `WOODPECKER_EXPERT_WEBHOOK_HOST` pointing to the in-cluster Woodpecker service.
- `WOODPECKER_EXPERT_FORGE_OAUTH_HOST` pointing to the local Gitea URL used by the browser/OAuth flow.

The runner performs a headless browser-style OAuth login, activates `filip/sample-app`, retrieves a Woodpecker API token, commits marker files to Gitea, and polls the Woodpecker API for the matching pipeline.

## Persistence And Agent Reconnect

Woodpecker stores its SQLite database on a persistent volume mounted at `/var/lib/woodpecker`. The installer restarts the agent after the server rollout so the agent reconnects to the current server database. This avoids stale agent/server state such as repeated `sql: no rows in result set` errors after a server recreation.

## Install And Run

```bash
make install-gitea
make install-woodpecker
make run-woodpecker
```

## Timeout

The default Woodpecker wait timeout is `300` seconds per warmup or measured run:

```yaml
ci_systems:
  - name: "woodpecker"
    timeout_seconds: 300
```

This keeps broken webhook, OAuth, or agent states from blocking for the global experiment timeout.

## Local UI

Woodpecker is configured with `http://localhost:30086`, but the default kind cluster does not map that NodePort to the host. Start a port-forward when you want the web UI:

```bash
kubectl -n pipelinebench-woodpecker port-forward service/woodpecker-server 30086:8000
```

Then open `http://localhost:30086` and sign in through Gitea OAuth. If Gitea is not already reachable in the browser, also run:

```bash
kubectl -n pipelinebench-gitea port-forward service/gitea-http 30082:3000
```
