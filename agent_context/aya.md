# Aya

## Scope
- Infra, Docker, Redis, MinIO, SFTP, Vault, CI

## Completed
- CI installs dependencies from `requirements.txt`.
- Added missing CI/runtime dependencies needed by infra/app imports.
- Added local default app/database settings so smoke tests can import app config without external env.
- Added top-level MinIO byte adapter for worker object storage.
- Added Redis/RQ adapter for enqueueing inference jobs.
- Added Paramiko SFTP client helpers for listing, downloading, and moving processed files.
- Reworked `sftp_ingest_worker` to create batches/documents through Mohamad services, upload TIFF bytes to MinIO, and enqueue Jad inference jobs.
- Added dev Docker Compose runtime wiring for API, Redis, Postgres, MinIO, SFTP, Vault, SFTP ingest worker, and inference worker.
- Added `migrate` service to Docker Compose.
- Switched Docker Compose values to `${VAR:-default}` interpolation so demo defaults can be overridden from environment.
- Fixed Casbin sync-engine startup config to use `DATABASE_SYNC_URL`; sqlite-only `check_same_thread` is now only used for sqlite URLs.
- Removed duplicate nested folders: `app/infra/infra/`, `docker/docker/`, and repo-root `jawad/`.
- Added infra import/config tests that do not require live Docker services.

## Files changed
- `requirements.txt`
- `app/core/config.py`
- `.env.example`
- `.github/workflows/ci.yml`
- `docker-compose.yml`
- `docker/api.Dockerfile`
- `docker/worker.Dockerfile`
- `docker/ingest.Dockerfile`
- `app/auth/casbin.py`
- `app/infra/blob/minio_client.py`
- `app/infra/queue/redis_client.py`
- `app/infra/queue/rq_client.py`
- `app/infra/queue/rq_queue.py`
- `app/infra/sftp/client.py`
- `app/infra/sftp/watcher.py`
- `app/workers/sftp_ingest_worker.py`
- `tests/infra/test_config.py`
- `tests/infra/test_infra_imports.py`
- `tests/infra/test_sftp_ingest_worker.py`
- Removed `app/infra/infra/`
- Removed `docker/docker/`
- Removed `jawad/`

## How to test
```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/smoke
.venv/bin/python -m pytest tests/infra
.venv/bin/python -m pytest --noconftest tests/classifier
.venv/bin/python app/classifier/eval/golden.py
.venv/bin/python -m py_compile app/core/config.py app/auth/casbin.py app/workers/sftp_ingest_worker.py
.venv/bin/python - <<'PY'
from app.core.config import settings
print("DATABASE_URL:", settings.DATABASE_URL)
from app.main import app
print("app import OK")
PY
```

## Blocked
- Full pytest now gets past the previous Casbin async URL bug, but API tests
  still require a running Postgres instance or a test DB override. Current
  error: `psycopg2.OperationalError: connection to server at "localhost" ...
  failed: Connection refused`.
- Ali routers are still expected to need session/service-signature fixes, but
  they were intentionally not changed in this Aya/Jad pass.
- Docker Compose config could not be validated locally because Docker is not
  available in this WSL distro.

## Contracts needed
- SFTP input folder contains `.tif` / `.tiff` files only for ingestion.
- Mohamad services remain available as `batch_service.create_batch(session, request_id)` and `batch_service.add_document(session, batch_id, filename, blob_bucket, blob_path)`.
- Jad inference worker remains enqueueable as `app.workers.inference_worker.classify_document_job`.

## Caveats / known limitations
- Local Docker builds currently install `requirements.txt`, which includes ML/runtime dependencies and may be heavy.
- The SFTP worker processes one batch per file for the demo path.
- Infra tests use fakes/import checks and intentionally do not require live Docker services.

## Next steps
- Run Docker Compose locally and verify end-to-end ingest from SFTP to MinIO to RQ to inference persistence.
- Copy measured local latency and smoke-test results into final demo docs/runbook.
