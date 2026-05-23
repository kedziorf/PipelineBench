# Experiment Runner

The Python runner coordinates benchmark runs for enabled local CI/CD providers.

Current provider lineup:

- Jenkins
- Tekton
- Concourse
- Gitea Actions
- Woodpecker CI

Defaults:

- five measured runs
- one warmup run
- Prometheus metric queries
- CSV, JSON, and log export
- global per-run timeout of `1800` seconds
- Woodpecker provider timeout override of `300` seconds

Run from the repository root:

```bash
python experiment-runner/main.py run --config experiment-runner/config.yaml --tool jenkins
```

Supported `--tool` values:

```text
jenkins
tekton
concourse
gitea-actions
woodpecker
```

Set Jenkins credentials with environment variables when needed:

```bash
export JENKINS_URL=http://localhost:8080
export JENKINS_USER=admin
export JENKINS_API_TOKEN=<token-or-password>
```

When using `make run-jenkins`, the wrapper script tries to read the Jenkins admin password from the `pipelinebench-jenkins` Kubernetes secret automatically.

Woodpecker, Gitea Actions, and Concourse use the shared local Gitea repository rather than local compatibility shims. CircleCI-compatible and GitLab-compatible local Job providers are not part of the final runner configuration.

## Configuration Notes

`experiment-runner/config.yaml` contains:

- `experiment`: run counts, global timeout, and cleanup behavior.
- `monitoring`: Prometheus URL and scrape settings.
- `gitea`: shared local forge URL, namespace, owner, and repository name.
- `ci_systems`: provider list, namespaces, metric namespaces, deployment method, and optional provider timeout.
- `results`: output location and export switches.

Provider-specific `metrics_namespaces` are aggregated into a single result row. Use this for providers such as Tekton that split controller and workload pods across namespaces.
