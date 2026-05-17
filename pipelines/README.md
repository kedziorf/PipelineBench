# Pipelines

Pipeline definitions live here and should execute the same benchmark steps for every CI/CD provider.

Provider-specific files can adapt syntax, but the logical steps should remain equivalent:

1. Checkout or prepare source.
2. Install Python dependencies.
3. Run unit tests.
4. Run CPU task.
5. Run memory task.
6. Build the Docker image when Docker is available.
7. Print final status and logs.
