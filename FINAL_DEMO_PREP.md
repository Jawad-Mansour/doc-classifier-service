# Final Demo Prep

## Purpose

This file is the code review and final demo prep sheet for the Week 6 Document Classifier project.
It explains:

- what the app does
- how the full flow works
- what each major service is doing
- how auth, RBAC, caching, storage, queueing, and inference work
- how the database is modeled and migrated
- how evaluation and testing were done
- what each important source file is responsible for
- what is complete and what is still a limitation

This is the file to review before presenting the system or defending design decisions.

---

## Project Summary

The project is a document classification system with:

- a FastAPI backend
- a React frontend dashboard
- PostgreSQL for persistent relational data
- Redis for queueing and API caching
- RQ workers for background jobs
- MinIO for object storage
- an SFTP ingestion source
- Vault for secret management in local demo/dev mode
- a PyTorch classifier running CPU inference

The current end-to-end product is centered around an SFTP ingestion pipeline:

1. A TIFF file is dropped into SFTP.
2. The ingest worker picks it up.
3. A batch and document are created in Postgres.
4. The raw file is stored in MinIO.
5. A Redis/RQ inference job is queued.
6. The inference worker downloads the image, runs the classifier, creates an overlay, and stores prediction results.
7. The API and frontend expose batches, predictions, audit logs, and role-controlled actions.

Important limitation:

- The frontend is currently an operations dashboard, not a browser upload product.
- There is no UI upload flow and no backend browser upload endpoint yet.
- Input is currently expected through SFTP as `.tif` or `.tiff`.

---

## High-Level Architecture

### Main layers

- `app/api/`: HTTP routes, schemas, middleware, FastAPI dependencies
- `app/auth/`: JWT and FastAPI Users wiring, Casbin integration
- `app/services/`: business logic and orchestration
- `app/repositories/`: SQLAlchemy queries and persistence
- `app/db/`: ORM models, base metadata, async session
- `app/domain/`: Pydantic domain models used between services and API
- `app/infra/`: external adapters for MinIO, Redis/RQ, SFTP, Vault
- `app/workers/`: long-running background workers
- `app/classifier/`: ML inference and evaluation code
- `frontend/src/`: React UI
- `alembic/`: database migration wiring and revisions

### Architectural rules followed

- API routes call services, not repositories directly.
- Repositories own SQL.
- Workers use services for persistence.
- The API does not run inference.
- The inference worker runs the classifier.
- Classifier code is isolated from FastAPI and SQLAlchemy.

---

## End-to-End Runtime Flow

## 1. Stack startup

`docker compose up` starts:

- `postgres`
- `redis`
- `minio`
- `sftp`
- `vault`
- `pgadmin`
- `migrate`
- `api`
- `frontend`
- `sftp-ingest-worker`
- `inference-worker`

Startup sequence matters:

- `migrate` must finish successfully before `api` starts
- `api` startup initializes secrets, RBAC policies, and demo users

## 2. Secret initialization

When `REQUIRE_VAULT=true`:

1. API startup checks that Vault is reachable.
2. The app reads `secret/data/doc-classifier`.
3. If required fields are missing, the app seeds them in Vault from current settings.
4. The app uses Vault values for:
   - `jwt_secret_key`
   - `database_password`
   - `minio_secret_key`
   - `sftp_password`

## 3. Auth and RBAC initialization

On startup:

- Casbin default policies are seeded idempotently.
- Demo users are seeded in Postgres when:
  - `DEBUG=true`
  - `SEED_DEMO_USERS=true`

Seeded users:

- `admin@example.com / Admin123!`
- `reviewer@example.com / Reviewer123!`
- `auditor@example.com / Auditor123!`

These users are persisted in the `users` table and survive API restarts as long as the Postgres volume remains.

## 4. SFTP ingestion

The live ingestion path is:

1. User or scanner places a `.tif` or `.tiff` file into the SFTP upload directory.
2. `app/workers/sftp_ingest_worker.py` polls the folder.
3. The worker validates the filename extension.
4. It creates a batch row and a document row.
5. It uploads the raw image bytes to MinIO.
6. It queues an RQ job in Redis.
7. It moves the file from `/upload` to `/processed`.

## 5. Inference

The inference worker:

1. dequeues the Redis job
2. downloads the image bytes from MinIO
3. preprocesses the image
4. validates the model SHA-256 against `model_card.json`
5. runs ConvNeXt Tiny inference
6. converts logits to:
   - `label_id`
   - `label`
   - `confidence`
   - `top5`
   - `all_probs`
   - `model_sha256`
7. generates an overlay PNG
8. uploads the overlay to MinIO
9. persists the prediction in Postgres
10. writes audit entries
11. updates batch status to `done`

If inference fails:

- the worker rolls back the active transaction
- batch status is updated to `failed`

## 6. API access

The frontend and other clients talk to:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/batches`
- `GET /api/v1/batches/{bid}`
- `GET /api/v1/predictions/recent`
- `PATCH /api/v1/predictions/{id}`
- `GET /api/v1/audit-log`
- `PATCH /api/v1/admin/users/{id}/role`

All protected endpoints require JWT auth and then pass through role/permission checks.

---

## What Each External Service Is

## PostgreSQL

PostgreSQL is the main relational database.

We use it for:

- users
- batches
- documents
- predictions
- audit logs
- Casbin policy storage

Why we need it:

- persistent structured data
- relationships between batches, documents, and predictions
- durable users and roles
- queryable audit history

## SQLAlchemy

SQLAlchemy is the Python ORM and DB toolkit.

We use:

- async SQLAlchemy for API/services/repositories
- sync SQLAlchemy only where Casbin adapter or Alembic need it

In this project SQLAlchemy is responsible for:

- table mapping
- session creation
- ORM object lifecycle
- query execution through repositories

## Alembic

Alembic is the migration tool for SQLAlchemy-managed schemas.

We use it to:

- define DB schema revisions
- apply schema changes consistently across environments
- bootstrap the database on container startup

How migration works here:

1. `alembic/env.py` loads SQLAlchemy metadata from `app.db.base.Base`.
2. `DATABASE_SYNC_URL` is used for migration connectivity.
3. `alembic/versions/0001_initial.py` creates the project tables.
4. The `migrate` container runs:

```bash
alembic upgrade head
```

Why `migrate` exits:

- because it is a one-shot job container
- successful exit is expected

## Redis

Redis is an in-memory data store.

We use it for two different things:

1. RQ job queue backend
2. API response cache backend

In this project Redis stores:

- queued inference jobs
- RQ job metadata/results
- FastAPI cache entries for selected endpoints

## RQ

RQ is Redis Queue.

We use it to push inference work out of the API path and into a background worker.

This matters because:

- inference is slower than normal API calls
- the API should stay responsive
- the ML pipeline should be decoupled from HTTP requests

## MinIO

MinIO is S3-compatible object storage.

We use it for binary files, not relational records.

In this project MinIO stores:

- raw uploaded SFTP images
- generated overlay PNGs

Why MinIO instead of Postgres:

- images are binary objects
- object stores are the correct tool for large file storage
- Postgres should keep metadata and references, not image blobs

Common object paths:

- `raw/batch_{batch_id}/{filename}`
- `overlays/batch_{batch_id}/{document_id}_overlay.png`

## SFTP

SFTP is the ingestion channel.

We use it because the project brief expects document ingestion from an external drop source rather than direct browser upload.

In this project:

- files appear in `/upload`
- processed files are moved to `/processed`
- the worker polls every few seconds

Currently accepted extensions:

- `.tif`
- `.tiff`

## Vault

Vault is the secrets manager.

We use Vault dev mode for the local demo. That is acceptable for this project because the requirement is local/dev secret management, not production Vault hardening.

We use Vault to hold:

- JWT secret
- database password
- MinIO secret key
- SFTP password

Current base path:

- `secret/data/doc-classifier`

Important point:

- env vars are still used for non-secret config
- Vault is used for secrets that the app reads at startup

---

## Auth and RBAC Design

## Authentication

Authentication is handled with `fastapi-users`.

Current source of truth:

- persistent `users` table in Postgres

Login flow:

1. client sends `POST /api/v1/auth/login`
2. FastAPI Users verifies email/password
3. JWT is signed using the configured secret
4. client stores bearer token
5. protected routes use that token to resolve the current user

## Authorization

Authorization is handled with Casbin.

Current subject design:

```text
subject = str(user.id)
```

That is important because the prior split-identity problem was fixed by aligning:

- JWT-authenticated user identity
- Postgres user id
- Casbin role assignment subject

Role assignment writes:

- `users.role`
- Casbin `g` relationship for `str(user.id)`

Roles:

- `admin`
- `reviewer`
- `auditor`

Permission examples:

- `admin`: manage roles, read batches, read predictions, relabel predictions, read audit log
- `reviewer`: read batches, read predictions, relabel predictions
- `auditor`: read batches, read audit log

Special relabel rule:

- reviewer cannot relabel predictions with confidence `>= 0.7`
- admin can relabel even high-confidence predictions

---

## Database Model

Tables created by the initial migration:

- `users`
- `batches`
- `documents`
- `predictions`
- `audit_logs`
- `casbin_rule`

## Entity meaning

### `users`

- persistent login accounts
- stores role in SQL as well as auth flags from FastAPI Users

### `batches`

- one ingestion event / request group
- tracks status:
  - `pending`
  - `processing`
  - `done`
  - `failed`

### `documents`

- one uploaded file entry tied to a batch
- stores filename and MinIO location for raw image

### `predictions`

- model output for a document
- stores label, confidence, top5, all_probs, model SHA, overlay path, relabel metadata

### `audit_logs`

- immutable event trail
- records actor, action, target, timestamp

### `casbin_rule`

- database-backed Casbin policies and role relationships

---

## Cache Design

Caching is implemented with `fastapi-cache` backed by Redis.

Current route namespaces:

- `/auth/me` -> `auth:me:{subject}`
- `/batches` -> `batches`
- `/batches/{bid}` -> `batch:{bid}`
- `/predictions/recent` -> `predictions:recent`

Why namespace consistency matters:

- the decorator namespace and invalidation namespace must match
- otherwise the app clears one key family while users still read stale data from another

Current invalidation behavior:

- batch create/update/document add -> clear `batches` and `batch:{batch_id}`
- prediction create/relabel -> clear `predictions:recent`, `batches`, and `batch:{batch_id}`
- role change -> clear `auth:me:{subject}`

---

## Classifier and Evaluation

## Model runtime

The model is a ConvNeXt Tiny classifier stored in:

- `app/classifier/models/classifier.pt`

Before use, the app validates:

- the SHA-256 of `classifier.pt`
- against the expected SHA declared in `model_card.json`

That protects against:

- stale artifacts
- accidental model swaps
- silent mismatch between code and expected model

## Preprocessing

The runtime preprocessing pipeline is:

1. open image with Pillow
2. convert to RGB
3. resize to `224x224`
4. convert to tensor
5. apply ImageNet normalization

## Output shape

Prediction output includes:

- `label_id`
- `label`
- `confidence`
- `top5`
- `all_probs`
- `model_sha256`

## Overlay generation

The worker creates an overlay PNG containing:

- predicted label
- confidence percentage

That overlay is stored in MinIO and referenced in the DB.

## How evaluation was done

There are several layers of verification:

### 1. Unit and service tests

These check:

- preprocessing
- predictor behavior
- inference worker behavior
- services
- RBAC logic
- Vault client
- cache invalidation behavior

### 2. API and route protection tests

These check:

- auth routes
- permission enforcement
- admin/reviewer/auditor access boundaries

### 3. Golden replay evaluation

`app/classifier/eval/golden.py` replays the saved model against a fixed set of golden TIFF images and verifies:

- model SHA matches
- predicted class matches expected class
- confidence stays within tolerance

This is the main regression guard for the classifier pipeline.

### 4. Live end-to-end workflow test

`tests/e2e/test_full_stack_workflow.py` validates the real stack:

- compose services
- auth
- SFTP ingest
- Postgres persistence
- Redis queueing
- MinIO storage
- worker inference
- prediction persistence
- overlay generation
- audit log

## Latest verified results

Verified in the current repo state:

- smoke/api/infra/RBAC/route protection passed
- classifier tests passed
- golden replay passed on 50 images
- non-E2E full pytest passed
- live full-stack workflow passed
- live admin relabel of a high-confidence prediction passed

---

## Frontend Role

The frontend is a role-aware dashboard built with React and Tailwind.

Current UI responsibilities:

- login
- fetch `/auth/me`
- show role-aware navigation
- show dashboard summary
- show recent predictions
- allow relabeling where permitted
- show batch list
- show audit log
- allow admin role changes

Current limitation:

- no browser upload flow
- no page for direct file submission
- no `multipart/form-data` upload API in backend

This means the frontend is currently a monitoring and operations UI for the SFTP-driven system.

---

## Source Map

This section is the quick review map of the important human-authored source files.

## Backend entrypoints

- `app/main.py`: FastAPI app factory, middleware, exception handlers, cache init, startup/shutdown hooks
- `app/api/main.py`: mounts all versioned API routers under `/api/v1`
- `docker-compose.yml`: local multi-service orchestration
- `docker/api.Dockerfile`: backend and migration image build
- `docker/worker.Dockerfile`: inference worker image build
- `docker/ingest.Dockerfile`: SFTP ingest worker image build
- `docker/frontend.Dockerfile`: frontend dev/build container

## API layer

- `app/api/routers/health.py`: `/health` and `/ready`
- `app/api/routers/auth.py`: login/register routers from FastAPI Users plus `/auth/me`
- `app/api/routers/batches.py`: list and fetch batches
- `app/api/routers/predictions.py`: recent predictions and relabel endpoint
- `app/api/routers/audit.py`: audit log read endpoint
- `app/api/routers/users.py`: admin-only role change endpoint
- `app/api/deps/auth.py`: current-user-with-role dependency; resolves Casbin role for authenticated user
- `app/api/deps/permissions.py`: reusable permission and role guards
- `app/api/middleware/request_id.py`: request tracing ID middleware
- `app/api/middleware/security_headers.py`: adds secure HTTP headers
- `app/api/schemas/__init__.py`: primary request/response models used by routes
- `app/api/schemas/common.py`: reusable health/error/message response shapes
- `app/api/schemas/auth.py`: package placeholder
- `app/api/schemas/batch.py`: package placeholder
- `app/api/schemas/prediction.py`: package placeholder
- `app/api/schemas/user.py`: package placeholder
- `app/api/exceptions.py`: API exception package file

## Auth and authorization

- `app/auth/users.py`: FastAPI Users SQLAlchemy adapter, user manager, login/register router wiring
- `app/auth/jwt.py`: JWT strategy configuration
- `app/auth/casbin.py`: Casbin model, role constants, resource/action constants, enforcer creation

## Core/configuration

- `app/core/config.py`: environment-driven settings for DB, Redis, MinIO, SFTP, Vault, auth, and demo users
- `app/core/security.py`: password hashing/verification, JWT/CORS/security settings validation
- `app/core/constants.py`: class names, confidence threshold, batch statuses, role enum
- `app/core/startup.py`: Vault secret wiring, policy seeding, demo user seeding
- `app/core/logging.py`: logging configuration and request id context
- `app/core/exceptions.py`: global exception response handlers

## Database and domain

- `app/db/base.py`: SQLAlchemy base metadata
- `app/db/models.py`: ORM table definitions
- `app/db/session.py`: async engine and session factory
- `app/domain/user.py`: user domain model
- `app/domain/batch.py`: batch domain model
- `app/domain/document.py`: document domain model
- `app/domain/prediction.py`: prediction domain model
- `app/domain/audit.py`: audit domain model

## Repositories

- `app/repositories/user_repository.py`: CRUD/query helpers for users
- `app/repositories/batch_repository.py`: batch create/read/status update
- `app/repositories/document_repository.py`: document create/read helpers
- `app/repositories/prediction_repository.py`: prediction create/read/update helpers
- `app/repositories/audit_repository.py`: audit insert/list helpers

## Services

- `app/services/user_service.py`: register user, seed demo users, change roles, protect last admin
- `app/services/role_service.py`: Casbin role assignment, role lookup, default policy seeding
- `app/services/batch_service.py`: batch lifecycle orchestration and cache invalidation
- `app/services/prediction_service.py`: prediction persistence, recent listing, relabel rules, cache invalidation
- `app/services/audit_service.py`: audit write/list orchestration
- `app/services/cache_service.py`: cache namespaces, custom key builders, invalidation helpers

## Infra adapters

- `app/infra/blob/minio_client.py`: MinIO byte upload/download wrapper
- `app/infra/queue/redis_client.py`: Redis connection factory
- `app/infra/queue/rq_client.py`: RQ queue and enqueue helper
- `app/infra/queue/rq_queue.py`: queue re-export convenience module
- `app/infra/sftp/client.py`: SFTP client wrapper and TIFF extension validator
- `app/infra/sftp/watcher.py`: thin SFTP helper functions
- `app/infra/vault/vault_client.py`: Vault health/read/write client
- `app/infra/cache/redis_cache.py`: cache package file
- `app/infra/logging/logger.py`: logging package file

## Workers

- `app/workers/sftp_ingest_worker.py`: polls SFTP, creates batch/document, stores raw object, enqueues inference, moves processed file
- `app/workers/inference_worker.py`: validates payload, runs model inference, uploads overlay, persists prediction, updates batch state

## Classifier

- `app/classifier/inference/preprocessing.py`: Pillow + torchvision preprocessing
- `app/classifier/inference/predictor.py`: model loading and prediction
- `app/classifier/inference/postprocessing.py`: logits -> domain prediction
- `app/classifier/inference/overlays.py`: overlay PNG generation
- `app/classifier/inference/model_validator.py`: artifact SHA and model card validation
- `app/classifier/inference/types.py`: strongly typed prediction output models
- `app/classifier/eval/golden.py`: golden replay regression evaluation
- `app/classifier/eval/golden_expected.json`: expected outputs for golden replay
- `app/classifier/eval/regenerate_golden_expected.py`: helper to regenerate golden expectations
- `app/classifier/models/classifier.pt`: trained model artifact
- `app/classifier/models/model_card.json`: model metadata and expected artifact SHA
- `app/classifier/training/train_colab.ipynb`: training notebook artifact

## Frontend

- `frontend/src/main.jsx`: React root mount
- `frontend/src/App.jsx`: app routes
- `frontend/src/api/client.js`: frontend API wrapper and bearer token handling
- `frontend/src/context/AuthContext.jsx`: auth state, login, logout, `/auth/me` bootstrap
- `frontend/src/components/Layout.jsx`: main shell layout
- `frontend/src/components/ProtectedRoute.jsx`: route guard
- `frontend/src/components/Sidebar.jsx`: role-aware navigation
- `frontend/src/components/Badge.jsx`: role/status badge styles
- `frontend/src/components/ConfidenceBar.jsx`: prediction confidence visualization
- `frontend/src/components/Spinner.jsx`: loading indicator
- `frontend/src/pages/Login.jsx`: login screen and demo credentials
- `frontend/src/pages/Dashboard.jsx`: summary dashboard for batches and predictions
- `frontend/src/pages/Predictions.jsx`: predictions table and relabel modal
- `frontend/src/pages/Batches.jsx`: batch list and status summaries
- `frontend/src/pages/AuditLog.jsx`: audit event timeline
- `frontend/src/pages/Users.jsx`: admin-only role change screen
- `frontend/src/index.css`: Tailwind base styles

## Tests

- `tests/api/test_auth.py`: auth API behavior
- `tests/api/test_auth_permissions.py`: permission-aware API behavior
- `tests/api/test_health.py`: health endpoints
- `tests/services/test_user_service.py`: user service behavior
- `tests/services/test_batch_service.py`: batch service and lifecycle behavior
- `tests/services/test_prediction_service.py`: prediction service and relabel rules
- `tests/infra/test_config.py`: config expectations
- `tests/infra/test_vault_client.py`: Vault and startup secret behavior
- `tests/infra/test_sftp_ingest_worker.py`: ingest worker behavior
- `tests/infra/test_infra_imports.py`: import smoke
- `tests/classifier/test_preprocessing.py`: preprocessing correctness
- `tests/classifier/test_predictor.py`: predictor correctness
- `tests/classifier/test_model_card_sha.py`: model SHA contract
- `tests/classifier/test_inference_worker.py`: inference worker persistence/overlay behavior
- `tests/smoke/tests_smoke/test_ingest.py`: smoke ingest contract
- `tests/test_rbac_permissions.py`: Casbin/RBAC policy behavior
- `tests/test_route_protection.py`: route protection expectations/template coverage
- `tests/e2e/test_full_stack_workflow.py`: live full-stack workflow
- `tests/BACKEND_TEST_RESULTS.md`: prior backend verification summary

## Migration files

- `alembic/env.py`: Alembic wiring to project metadata and sync DB URL
- `alembic/versions/0001_initial.py`: creates initial schema
- `alembic.ini`: Alembic config

---

## Operational Notes

## Why `migrate` exits

That is expected.

`migrate` is a one-off container that runs:

```bash
alembic upgrade head
```

Once it succeeds, it exits with code `0`.

## Why `inference-worker` might exit

That is not intended as steady-state behavior.

Observed cause in logs:

- Redis connection timeout

Meaning:

- the worker started correctly
- did work correctly
- then lost Redis connectivity and quit cleanly

Recommended hardening:

- add `restart: unless-stopped` for long-running services such as:
  - `api`
  - `inference-worker`
  - `sftp-ingest-worker`

## Why images are not stored in Postgres

Because Postgres stores structured records, not document binaries efficiently.

We store:

- metadata in Postgres
- raw files and overlays in MinIO

That split is the correct architecture for this kind of app.

---

## Known Limitations

- No browser upload flow yet
- No backend `multipart/form-data` upload endpoint yet
- Current ingestion is SFTP-only
- File validation is extension-based for ingest, not deep content verification
- Current `/ready` endpoint is still shallow and returns a placeholder success response
- Long-running workers should ideally have restart policies in Compose
- Current UI assumes the backend pipeline already produced data

---

## Demo Talking Points

If asked "what makes this production-like?" the strongest answers are:

- persistent auth users in Postgres
- RBAC enforced by Casbin with DB-backed policies
- secrets sourced from Vault
- object storage separated from relational storage
- background inference through Redis/RQ workers
- audit trail for sensitive actions
- cache invalidation tied to route namespaces
- model integrity verified by SHA-256
- golden replay regression checks
- live end-to-end workflow test over the full stack

If asked "what is still missing?" the honest answer is:

- direct browser upload
- broader file-type ingestion and conversion
- stronger readiness checks
- better Compose restart policy hardening

---

## Useful Demo URLs

- Frontend: `http://localhost:3000`
- API: `http://localhost:8080`
- API docs: `http://localhost:8080/api/docs`
- pgAdmin: `http://localhost:5050`
- MinIO console: `http://localhost:9001`
- Vault: `http://localhost:8200`

---

## Demo Credentials

- Admin: `admin@example.com / Admin123!`
- Reviewer: `reviewer@example.com / Reviewer123!`
- Auditor: `auditor@example.com / Auditor123!`

