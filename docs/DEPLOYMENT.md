# Deployment

Local mode uses SQLite and synchronous jobs. Compose demonstrates API, Next.js, PostgreSQL, and Redis. Production should use an external TLS reverse proxy, managed PostgreSQL/Redis, S3-compatible evidence storage, dedicated workers, migration-only release jobs, immutable images, health probes, backups, and observability.

```bash
cp .env.example .env
docker compose config
docker compose up --build
```

The latest local verification environment did not contain the Docker CLI, so container execution is not claimed. Backend checks and API smoke tests were run directly; frontend package installation timed out locally, while CI remains configured to run clean frontend checks on Linux.
