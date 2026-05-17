# Experiment Runner

The Python runner coordinates benchmark runs for enabled CI/CD providers.

Current MVP:

- Jenkins, Tekton, and CircleCI-compatible local providers
- five measured runs by default
- one warmup run by default
- Prometheus metric queries
- CSV, JSON, and log export

Run from the repository root:

```bash
python experiment-runner/main.py run --config experiment-runner/config.yaml --tool jenkins
```

Use `--tool tekton` for the Tekton provider or `--tool circleci` for the local CircleCI-compatible provider.

Set Jenkins credentials with environment variables:

```bash
export JENKINS_URL=http://localhost:8080
export JENKINS_USER=admin
export JENKINS_API_TOKEN=<token-or-password>
```

When using `make run-jenkins`, the wrapper script tries to read the Jenkins admin password from the `pipelinebench-jenkins` Kubernetes secret automatically.

The CircleCI-compatible provider is fully local. It creates Kubernetes Jobs in `pipelinebench-circleci` and does not call CircleCI Cloud or the CircleCI API.
