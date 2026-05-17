SHELL := /usr/bin/env bash
export PATH := $(CURDIR)/.tools/bin:$(PATH)

.PHONY: check-tools create-cluster delete-cluster install-monitoring install-jenkins run-jenkins run-benchmark clean clean-all
.PHONY: install-tekton run-tekton

check-tools:
	./scripts/check-tools.sh

create-cluster:
	./scripts/create-cluster.sh

delete-cluster:
	./scripts/delete-cluster.sh

install-monitoring:
	./scripts/install-monitoring.sh

install-jenkins:
	./scripts/install-jenkins.sh

install-tekton:
	./scripts/install-tekton.sh

run-jenkins:
	./scripts/run-benchmark.sh jenkins

run-tekton:
	./scripts/run-benchmark.sh tekton

run-benchmark:
	./scripts/run-benchmark.sh jenkins

clean:
	python3 experiment-runner/main.py cleanup --config experiment-runner/config.yaml

clean-all:
	./scripts/clean-all.sh
