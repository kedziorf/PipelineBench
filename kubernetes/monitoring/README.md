# Monitoring Manifests

The MVP installs monitoring with Helm using `helm/values/prometheus-values.yaml`.

Prometheus, kube-state-metrics, and node exporter are provided by `kube-prometheus-stack`. Metrics Server is installed separately because it is useful for Kubernetes resource inspection even when Prometheus is the main metrics source.
