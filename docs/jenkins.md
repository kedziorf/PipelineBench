# Jenkins Provider

The Jenkins provider installs a local Jenkins controller in `pipelinebench-jenkins` using the Jenkins Helm chart. Jenkins runs inside the kind cluster and uses the PipelineBench Jenkinsfile from `pipelines/jenkins/`.

## Source And Pipeline

The Jenkins pipeline fetches the workload archive from the shared local Gitea repository. This keeps Jenkins on the same local source forge as Tekton, Concourse, Gitea Actions, and Woodpecker.

The workload stages mirror the common benchmark shape:

1. Python unit tests.
2. CPU benchmark task.
3. Memory benchmark task.
4. Docker build check, skipped when Docker is unavailable.

## Install And Run

```bash
make install-jenkins
make run-jenkins
```

`make run-jenkins` tries to read the Jenkins admin password from the Kubernetes secret automatically. If needed, set credentials manually:

```bash
export JENKINS_URL=http://localhost:8080
export JENKINS_USER=admin
export JENKINS_API_TOKEN=<jenkins-admin-password-or-api-token>
```

## Local UI

Jenkins is mapped directly by the kind cluster config:

```text
http://localhost:8080
```

Retrieve the initial admin password with:

```bash
kubectl -n pipelinebench-jenkins get secret pipelinebench-jenkins   -o jsonpath='{.data.jenkins-admin-password}' | base64 --decode
```
