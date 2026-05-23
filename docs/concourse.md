# Concourse Provider

The Concourse provider installs a real local Concourse deployment in `pipelinebench-concourse` using the official Concourse Helm chart. Concourse includes web, worker, and PostgreSQL components.

PipelineBench uses the local `fly` CLI downloaded from the Concourse web node to set the pipeline, unpause it, trigger the `sample-app` job, watch completion, and capture logs.

## Source And Pipeline

The pipeline uses the shared local Gitea repository as a Concourse `git` resource. PipelineBench sets and triggers the provider-specific pipeline from `pipelines/concourse/`.

## Install And Run

```bash
make install-concourse
make run-concourse
```

## Local UI

Concourse is configured with the external URL `http://localhost:30084`, but the default kind cluster does not map that NodePort to the host. Start a port-forward when you want the web UI:

```bash
kubectl -n pipelinebench-concourse port-forward service/pipelinebench-concourse-web 30084:8080
```

Then open `http://localhost:30084` and sign in with `test` / `test`.
