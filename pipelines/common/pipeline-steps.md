# Common Pipeline Steps

All providers should execute equivalent steps:

1. Prepare the repository content.
2. Install workload dependencies from `workloads/sample-app/requirements.txt`.
3. Run workload tests with `pytest`.
4. Run `benchmark/cpu_task.py`.
5. Run `benchmark/memory_task.py`.
6. Attempt a Docker image build when Docker is available.
7. Emit final status and logs.
