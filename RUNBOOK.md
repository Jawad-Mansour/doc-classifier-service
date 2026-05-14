# Runbook

## Purpose

This runbook covers local startup, smoke validation, common operational checks, and recovery steps for the Week 6 document-classifier stack.

## Prerequisites

- Docker and Docker Compose
- Git LFS available for `classifier.pt`
- Python 3 for running the standalone smoke script on the host

## First Boot

```bash
cp .env.example .env
docker compose up -d
```

Key URLs:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8080`
- Swagger: `http://localhost:8080/api/docs`
- pgAdmin: `http://localhost:5050`
- MinIO console: `http://localhost:9001`
- Vault: `http://localhost:8200`

Demo accounts:

- `admin@example.com` / `Admin123!`
- `reviewer@example.com` / `Reviewer123!`
- `auditor@example.com` / `Auditor123!`

## Health Checks

Fast checks:

```bash
docker compose ps
curl -s http://localhost:8080/api/v1/health
curl -s http://localhost:8080/api/v1/ready
```

The readiness endpoint now checks:

- Postgres
- Redis
- MinIO bucket reachability
- Vault reachability when `REQUIRE_VAULT=true`

## Full Smoke Test

Run the live end-to-end workflow:

```bash
python3 tests/e2e/test_full_stack_workflow.py
```

This validates:

- compose startup
- health and readiness
- Vault, Redis, and Postgres reachability
- user registration/login
- SFTP drop ingestion
- MinIO raw and overlay objects
- RQ job processing
- prediction persistence
- audit-log persistence

The report is written to `tmp/full_stack_workflow_report.md`.

## Targeted Test Commands

```bash
docker compose run -T --rm inference-worker python -m pytest tests/smoke tests/api tests/infra tests/test_rbac_permissions.py tests/test_route_protection.py
docker compose run -T --rm inference-worker python -m pytest tests/services
docker compose run -T --rm inference-worker python -m pytest --noconftest tests/classifier
docker compose run -T --rm inference-worker python app/classifier/eval/golden.py
docker compose run -T --rm frontend npm run build
```

## Common Operations

Re-run migrations:

```bash
docker compose run -T --rm migrate
```

Restart only a single service:

```bash
docker compose restart api
docker compose restart inference-worker
docker compose restart sftp-ingest-worker
```

Inspect logs:

```bash
docker compose logs --tail=100 api
docker compose logs --tail=100 inference-worker
docker compose logs --tail=100 sftp-ingest-worker
docker compose logs --tail=100 vault
```

## Troubleshooting

If `/api/v1/ready` fails:

- check `docker compose ps`
- inspect `api`, `postgres`, `redis`, `minio`, and `vault` logs
- verify `VAULT_TOKEN` in `.env`

If UI upload stalls:

- check `api` accepted `POST /api/v1/classify`
- check `inference-worker` logs for the queued batch id
- fetch `/api/v1/batches/{id}` and `/api/v1/predictions/batch/{id}`

If SFTP ingestion fails:

- ensure `sftp-ingest-worker` is running
- inspect `/home/test/upload` and `/home/test/processed` inside the `sftp` container
- confirm only TIFF files are expected on the SFTP path

If Vault blocks startup:

- `curl http://localhost:8200/v1/sys/health`
- confirm `VAULT_TOKEN=root` unless you intentionally changed it

## Reset

Non-destructive restart:

```bash
docker compose down
docker compose up -d
```

Destructive local reset:

```bash
docker compose down -v --remove-orphans
docker compose up -d
```

Use the destructive reset only when you are willing to lose local Postgres and MinIO data.
