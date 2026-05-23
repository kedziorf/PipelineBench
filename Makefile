SHELL := /usr/bin/env bash
export PATH := $(CURDIR)/.tools/bin:$(PATH)

.PHONY: check-tools create-cluster delete-cluster install-monitoring install-gitea seed-gitea-repo install-jenkins run-jenkins install-tekton run-tekton install-concourse run-concourse install-gitea-actions run-gitea-actions install-woodpecker run-woodpecker run-benchmark compare-results clean clean-all

check-tools:
	./scripts/check-tools.sh

create-cluster:
	./scripts/create-cluster.sh

delete-cluster:
	./scripts/delete-cluster.sh

install-monitoring:
	./scripts/install-monitoring.sh

install-gitea:
	./scripts/install-gitea.sh

seed-gitea-repo:
	./scripts/seed-gitea-repo.sh

install-jenkins:
	./scripts/install-jenkins.sh

install-tekton:
	./scripts/install-tekton.sh

install-concourse:
	./scripts/install-concourse.sh

install-gitea-actions:
	./scripts/install-gitea-actions.sh

install-woodpecker:
	./scripts/install-woodpecker.sh

run-jenkins:
	./scripts/run-benchmark.sh jenkins

run-tekton:
	./scripts/run-benchmark.sh tekton

run-concourse:
	./scripts/run-benchmark.sh concourse

run-gitea-actions:
	./scripts/run-benchmark.sh gitea-actions

run-woodpecker:
	./scripts/run-benchmark.sh woodpecker

run-benchmark:
	./scripts/run-benchmark.sh jenkins

compare-results:
	python3 scripts/compare-results.py

clean:
	python3 experiment-runner/main.py cleanup --config experiment-runner/config.yaml

clean-all:
	./scripts/clean-all.sh
