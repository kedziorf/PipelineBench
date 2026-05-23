# Gitea Actions Provider

The Gitea Actions provider uses the shared local Gitea forge plus an `act_runner` deployment in `pipelinebench-gitea-actions`. The runner uses Docker-in-Docker so workflow jobs run through the real Gitea Actions runner flow while remaining local to the kind cluster.

## Source And Triggering

PipelineBench triggers a run by committing a small marker file to the local Gitea repository. Gitea Actions then runs the workflow from `pipelines/gitea-actions/`, and the provider watches the local Gitea SQLite database for the workflow run associated with that commit.

The database polling path is intentional for the current local setup because Gitea 1.24 can return `404` for the Actions run REST API while the run records are still present in SQLite.

## Install And Run

```bash
make install-gitea
make install-gitea-actions
make run-gitea-actions
```

## Local UI

Gitea Actions does not expose a separate provider UI. Use the shared Gitea web interface:

```bash
kubectl -n pipelinebench-gitea port-forward service/gitea-http 30082:3000
```

Then open `http://localhost:30082`, sign in with `filip` / `pipelinebench-local-password`, and inspect `filip/sample-app`.
