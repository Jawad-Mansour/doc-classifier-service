# Document Classifier Service

Week 6 project for the AIE Program: an authenticated document-classification service that runs locally with `docker compose`, ingests scanner-style TIFF drops over SFTP, stores raw and derived assets in MinIO, queues inference through Redis/RQ, and exposes predictions through a role-gated FastAPI API and frontend.

## What ships

- FastAPI API with JWT auth via `fastapi-users`
- Casbin RBAC with `admin`, `reviewer`, and `auditor`
- SFTP ingest worker and RQ inference worker
- Postgres + Alembic migrations
- Redis-backed queue and `fastapi-cache2`
- MinIO object storage for raw uploads and overlay PNGs
- Vault dev mode for local secret resolution at startup
- ConvNeXt Tiny classifier artifact, model card, and 50-image golden replay set

## Brief Alignment

Implemented against the brief:

- API never runs inference; the worker does
- SFTP -> MinIO -> Redis/RQ -> worker -> Postgres pipeline works
- Browser upload also exists, but it feeds the same queue-backed worker pipeline
- Vault is required for the API in compose and the app refuses startup if Vault is unreachable
- Cached reads exist for `/auth/me`, `/batches`, `/batches/{id}`, and `/predictions/recent`
- Golden replay passes from the shipped model artifacts
- Live full-stack smoke workflow exists at `tests/e2e/test_full_stack_workflow.py`

Still not fully brief-complete:

- `mypy app` is not green yet
- The brief's strict `grep -ri 'password' app/` rule is not yet satisfied
- `COLLABORATION.md` still needs the real Trello URL and the team's final write-up before submission

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

Primary local URLs:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8080`
- API docs: `http://localhost:8080/api/docs`
- pgAdmin: `http://localhost:5050`
- MinIO console: `http://localhost:9001`
- Vault: `http://localhost:8200`

Demo users seeded in local debug mode:

- `admin@example.com` / `Admin123!`
- `reviewer@example.com` / `Reviewer123!`
- `auditor@example.com` / `Auditor123!`

## Runtime Flows

SFTP ingestion flow:

1. A `.tif` or `.tiff` file lands in the SFTP `/upload` directory.
2. `sftp-ingest-worker` validates the file, uploads it to MinIO, creates batch/document rows, and enqueues an RQ job.
3. `inference-worker` downloads the bytes, validates the model SHA, runs inference, stores the overlay PNG, writes the prediction row, and records audit/cache updates.

Browser upload flow:

1. A reviewer or admin uploads `.tif`, `.tiff`, `.png`, `.jpg`, or `.jpeg` through `POST /api/v1/classify`.
2. The API stores the raw file in MinIO, creates the batch/document rows, and enqueues the same worker job.
3. The frontend polls the batch until it reaches `done`, then fetches `/predictions/batch/{id}` and renders `top5`.

## Public API

Auth:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

Core reads:

- `GET /api/v1/batches`
- `GET /api/v1/batches/{id}`
- `GET /api/v1/predictions/recent`
- `GET /api/v1/predictions/batch/{batch_id}`
- `GET /api/v1/audit-log`

Writes:

- `POST /api/v1/classify`
- `PATCH /api/v1/predictions/{id}`
- `PATCH /api/v1/admin/users/{id}/role`

Role behavior:

- `admin`: manage roles, read predictions, relabel predictions, read batches, read audit log
- `reviewer`: read predictions, relabel when confidence `< 0.7`, read batches
- `auditor`: read-only on batches and audit log

## Model Summary

Derived from [`app/classifier/models/model_card.json`](app/classifier/models/model_card.json):

- Backbone: `convnext_tiny`
- Weights enum: `ConvNeXt_Tiny_Weights.DEFAULT`
- Freeze policy: `partial_unfreeze_last_convnext_stage_plus_classifier_full_train_epoch2`
- Full test split top-1: `0.7942198554963874`
- Full test split top-5: `0.9619490487262181`
- Worst full-test class: `scientific_report` at `0.6120896717373899`
- Artifact SHA-256: `219501b3dae668c7834376fb201468ea073614511be49e66bf1e7f6b4ce1f754`

Golden replay contract:

- Script: `python app/classifier/eval/golden.py`
- Pass rule: labels must match and top-1 confidence must be within `1e-6`

## Latency Budget

Committed demo budgets from the brief:

- Cached API reads: `p95 < 50ms`
- Uncached API reads: `p95 < 200ms`
- End-to-end single-document flow: `p95 < 10s`

Recent local live checks on this branch completed single-document end-to-end processing in roughly `4s` to `6s` on the current CPU-only Docker stack.

## Tests

Important commands:

```bash
docker compose run -T --rm inference-worker python -m pytest tests/smoke tests/api tests/infra tests/test_rbac_permissions.py tests/test_route_protection.py
docker compose run -T --rm inference-worker python -m pytest tests/services
docker compose run -T --rm inference-worker python -m pytest --noconftest tests/classifier
docker compose run -T --rm inference-worker python app/classifier/eval/golden.py
python3 tests/e2e/test_full_stack_workflow.py
```

The CI workflow currently builds the stack, runs the backend/classifier suites, runs golden replay, and runs the live full-stack smoke script.

## Docs

- `ARCH.md`: architecture walkthrough
- `DECISIONS.md`: architectural decisions and tradeoffs
- `RUNBOOK.md`: setup, smoke tests, and troubleshooting
- `SECURITY.md`: auth, secrets, and risk notes
- `COLLABORATION.md`: team ownership and Trello submission notes

## Submission Checklist

Before tagging `v0.1.0-week6`, fill the remaining human-owned items:

1. Put the real repo URL, Trello URL, and full team names into `COLLABORATION.md`.
2. Confirm the working tree is committed and the tag points at the final state.
3. Decide whether to accept the current `mypy` and password-grep gaps or fix them before submission.
