# Architecture

## System Overview

An internal document classification service that runs on a developer laptop via `docker-compose`.
A scanner drops TIFF files over SFTP → a pipeline classifies them using a ConvNeXt Tiny model → authenticated users browse results through a permission-gated REST API.

---

## Full Workflow — Start to Finish

```
Scanner drops invoice.tiff onto SFTP server
        │
        ▼
app/workers/sftp_ingest_worker.py
  polls SFTP every 5 seconds
  validates file is a real TIFF
        │
        ▼
app/services/batch_service.py  →  app/repositories/batch_repository.py  →  PostgreSQL
  create_batch(session, request_id)
  add_document(session, batch_id, filename, bucket, path)
        │
        ▼
app/infra/blob/minio_client.py
  uploads invoice.tiff to MinIO at: raw/batch_{id}/invoice.tiff
        │
        ▼
app/infra/queue/rq_queue.py
  pushes job to Redis:
  { job_id, batch_id, document_id, blob_bucket, blob_path, original_filename, request_id }
        │
        ▼
app/workers/inference_worker.py
  dequeues job from Redis
        │
        ▼
app/infra/blob/minio_client.py
  downloads invoice.tiff bytes from MinIO
        │
        ▼
app/classifier/inference/preprocessing.py
  resizes to 224×224, converts to RGB, normalises
        │
        ▼
app/classifier/inference/predictor.py
  loads classifier.pt once at startup
  runs ConvNeXt Tiny forward pass
        │
        ▼
app/classifier/inference/postprocessing.py
  converts logits → label, confidence, top5, all_probs
        │
        ▼
app/classifier/inference/overlays.py
  draws label + confidence on the image → overlay PNG bytes
        │
        ▼
app/infra/blob/minio_client.py
  uploads overlay PNG to MinIO at: overlays/batch_{id}/{doc_id}_overlay.png
        │
        ▼
app/services/prediction_service.py  →  app/repositories/prediction_repository.py  →  PostgreSQL
  create_prediction(session, all 13 fields)
        │
        ├──▶ app/services/audit_service.py  →  app/repositories/audit_repository.py  →  PostgreSQL
        │      log_event("prediction_created") — flushed, not committed yet
        │
        ├──▶ session.commit()  — prediction + audit log written atomically
        │
        └──▶ app/services/cache_service.py  →  Redis
               invalidate_predictions() — clears "predictions:recent" cache
        │
        ▼
Result is now in the database and visible via the API

════════════════════════════════════════════════════════════
USER BROWSES THE RESULT
════════════════════════════════════════════════════════════

User sends: POST /auth/login  { email, password }
        │
        ▼
app/api/routers/auth.py
        │
        ▼
app/auth/users.py  (fastapi-users)
  verifies credentials against users table in PostgreSQL
        │
        ▼
app/auth/jwt.py
  issues signed JWT  ← signing key fetched from Vault at startup
        │
        ▼
User receives JWT token

────────────────────────────────────────────────────────────

User sends: GET /predictions/recent
  Authorization: Bearer <token>
        │
        ▼
app/api/middleware/request_id.py
  assigns UUID to request (X-Request-ID header)
        │
        ▼
app/api/deps/auth.py
  validates JWT → extracts user identity
        │
        ▼
app/api/deps/permissions.py  →  app/auth/casbin.py
  checks: does this user's role allow READ on /predictions?
  admin   → YES
  reviewer → YES
  auditor → NO → HTTP 403
        │
        ▼
app/api/routers/predictions.py
  @cache(namespace="predictions:recent")
        │
        ├── Cache HIT  →  returns Redis response directly  (p95 < 50ms)
        │
        └── Cache MISS →
                │
                ▼
              app/services/prediction_service.py
                get_recent(session)
                │
                ▼
              app/repositories/prediction_repository.py
                SQL: SELECT * FROM predictions ORDER BY created_at DESC LIMIT 20
                │
                ▼
              PostgreSQL → rows returned
                │
                ▼
              app/domain/prediction.py
                ORM rows → PredictionDomain (Pydantic)
                │
                ▼
              app/api/schemas/__init__.py
                PredictionDomain → PredictionResponse (JSON shape)
                │
                ▼
              result cached in Redis for 60s  (p95 < 200ms)
        │
        ▼
JSON response returned to user

════════════════════════════════════════════════════════════
REVIEWER RELABELS A PREDICTION
════════════════════════════════════════════════════════════

Reviewer sends: PATCH /predictions/{id}  { new_label: "budget" }
        │
        ▼
app/api/deps/permissions.py  →  app/auth/casbin.py
  reviewer role → allowed to UPDATE predictions
        │
        ▼
app/api/routers/predictions.py
  calls relabel(session, id, new_label, reviewer_email)
        │
        ▼
app/services/prediction_service.py
  fetches prediction from DB
  GUARD: if confidence >= 0.7 → raise UnauthorizedRelabel → HTTP 403
  GUARD: if prediction not found → raise PredictionNotFound → HTTP 404
        │
        ▼
app/repositories/prediction_repository.py
  UPDATE predictions SET label=... WHERE id=...
        │
        ▼
app/services/audit_service.py  →  app/repositories/audit_repository.py
  log_event(actor=reviewer_email, action="relabel", target="prediction:{id}")
        │
        ▼
session.commit()  — relabel + audit log written atomically
        │
        ▼
app/services/cache_service.py  →  Redis
  invalidate_predictions()
        │
        ▼
HTTP 200 — updated prediction returned

════════════════════════════════════════════════════════════
ADMIN CHANGES A USER ROLE
════════════════════════════════════════════════════════════

Admin sends: PATCH /admin/users/{id}/role  { role: "reviewer" }
        │
        ▼
app/api/deps/permissions.py  →  app/auth/casbin.py
  only admin role → allowed
        │
        ▼
app/api/routers/users.py
  calls toggle_role(session, id, new_role, admin_email)
        │
        ▼
app/services/user_service.py
  GUARD: if demoting the last admin → raise LastAdminError → HTTP 400
  GUARD: if user not found → raise UserNotFound → HTTP 404
        │
        ▼
app/repositories/user_repository.py
  UPDATE users SET role=... WHERE id=...
        │
        ▼
app/services/role_service.py  →  app/auth/casbin.py
  updates Casbin policy in casbin_rule table
        │
        ▼
app/services/audit_service.py
  log_event(actor=admin_email, action="role_change", target="user:{id}")
        │
        ▼
session.commit()
        │
        ▼
app/services/cache_service.py  →  Redis
  invalidate_auth_user(user_id)
        │
        ▼
On the affected user's NEXT request → new permissions apply immediately
No logout required
```

---

## All Files and Their Role

### Ali — API + Auth + Permissions

| File | Role |
|---|---|
| `app/main.py` | Creates the FastAPI app, registers all middleware, routers, exception handlers, and initialises FastAPICache on startup |
| `app/api/routers/auth.py` | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| `app/api/routers/batches.py` | `GET /batches`, `GET /batches/{id}` — injects session, checks permissions, applies cache |
| `app/api/routers/predictions.py` | `GET /predictions/recent`, `PATCH /predictions/{id}` — maps domain exceptions to HTTP codes |
| `app/api/routers/users.py` | `PATCH /admin/users/{id}/role` — admin only, calls `toggle_role` |
| `app/api/routers/audit.py` | `GET /audit-log` — read-only, admin and auditor |
| `app/api/routers/health.py` | `GET /health` — liveness check |
| `app/api/deps/auth.py` | FastAPI dependency — reads JWT from header, returns current user |
| `app/api/deps/permissions.py` | FastAPI dependency — checks Casbin before every protected endpoint |
| `app/api/schemas/__init__.py` | Pydantic response shapes returned as JSON (BatchResponse, PredictionResponse, etc.) |
| `app/api/middleware/request_id.py` | Assigns a UUID to every request for end-to-end log tracing |
| `app/api/middleware/security_headers.py` | Adds security HTTP headers to every response |
| `app/auth/jwt.py` | JWT signing strategy — key injected from Vault at startup |
| `app/auth/casbin.py` | Casbin enforcer — defines which role can do what on which resource |
| `app/auth/users.py` | fastapi-users wiring — SQLAlchemy adapter, user manager, login and register routers |
| `app/core/security.py` | `hash_pwd()` and `verify_pwd()` using bcrypt, CORS and security settings |

---

### Mohamad — DB + Services + Repositories

| File | Role |
|---|---|
| `app/exceptions.py` | 6 domain exceptions: `UserNotFound`, `BatchNotFound`, `DocumentNotFound`, `PredictionNotFound`, `LastAdminError`, `UnauthorizedRelabel` |
| `app/core/constants.py` | `CLASS_NAMES` list, `CONFIDENCE_THRESHOLD = 0.7`, `BatchStatus` and `UserRole` enums |
| `app/db/base.py` | SQLAlchemy `DeclarativeBase` — one line, inherited by all ORM models |
| `app/db/models.py` | 6 ORM table definitions: `User`, `Batch`, `Document`, `Prediction`, `AuditLog`, `CasbinRule` |
| `app/db/session.py` | Async session factory, `get_session` dependency, `dispose_engine` on shutdown |
| `app/domain/user.py` | `UserDomain` — clean Pydantic user shape, hashed_pwd excluded |
| `app/domain/batch.py` | `BatchDomain` — `id, request_id, status, created_at` |
| `app/domain/document.py` | `DocumentDomain` — `id, batch_id, filename, blob_bucket, blob_path` |
| `app/domain/prediction.py` | `PredictionDomain` — all 14 fields including `top5`, `all_probs`, `relabeled_by` |
| `app/domain/audit.py` | `AuditLogDomain` — `id, actor, action, target, timestamp` |
| `app/repositories/user_repository.py` | Pure SQL for users: `create`, `get_by_id`, `get_by_email`, `update_role`, `count_by_role` |
| `app/repositories/batch_repository.py` | Pure SQL for batches: `create`, `get_by_id`, `list_all`, `update_status` |
| `app/repositories/document_repository.py` | Pure SQL for documents: `create`, `get_by_id`, `list_by_batch` |
| `app/repositories/prediction_repository.py` | Pure SQL for predictions: `create`, `get_by_id`, `get_recent`, `list_by_batch_id`, `update_label` |
| `app/repositories/audit_repository.py` | Pure SQL for audit log: `create`, `list_all`, `list_by_actor` — append-only |
| `app/services/audit_service.py` | `log_event()` flushes but does NOT commit — parent service commits atomically |
| `app/services/cache_service.py` | `invalidate_batch()`, `invalidate_predictions()`, `invalidate_auth_user()` — clears Redis after writes |
| `app/services/batch_service.py` | `create_batch`, `add_document`, `get_batch`, `list_batches`, `update_status` |
| `app/services/prediction_service.py` | `create_prediction`, `get_recent`, `list_predictions`, `relabel` (guards confidence < 0.7) |
| `app/services/user_service.py` | `register_user`, `toggle_role` (guards last admin demotion) |

---

### Jad — ML + Inference

| File | Role |
|---|---|
| `app/classifier/models/classifier.pt` | Trained ConvNeXt Tiny weights (~110MB, stored in git LFS) |
| `app/classifier/models/model_card.json` | SHA-256, top-1/top-5 accuracy, per-class accuracy, backbone, freeze policy, environment fingerprint |
| `app/classifier/models/labels.json` | Mapping of class index to class name |
| `app/classifier/inference/preprocessing.py` | Resizes TIFF to 224×224, converts to RGB, normalises with ImageNet mean/std |
| `app/classifier/inference/predictor.py` | Loads model once at startup, exposes `predict_bytes(image_bytes) → PredictionResult` |
| `app/classifier/inference/postprocessing.py` | Converts raw logits → `label`, `confidence`, `top5`, `all_probs` |
| `app/classifier/inference/overlays.py` | Draws predicted label and confidence on image → returns PNG bytes |
| `app/classifier/inference/types.py` | `PredictionResult` and `TopKPrediction` Pydantic models |
| `app/classifier/eval/golden.py` | Replays 50 golden images — pass = byte-identical labels, confidence within 1e-6. Fail blocks CI |
| `app/classifier/eval/golden_expected.json` | Expected labels and confidences for all 50 golden images |
| `app/classifier/eval/golden_images/` | The 50 TIFF images used in the replay test |
| `app/workers/inference_worker.py` | Dequeues RQ job → downloads TIFF → runs model → uploads overlay → saves prediction via service |

---

### Aya — Infrastructure + DevOps + Ingest

| File | Role |
|---|---|
| `docker-compose.yml` | Defines all 9 containers and their dependencies, ports, and env vars |
| `docker/api.Dockerfile` | Builds the FastAPI API container image |
| `docker/worker.Dockerfile` | Builds the inference worker container image |
| `docker/ingest.Dockerfile` | Builds the SFTP ingest worker container image |
| `.env.example` | Template — holds only Vault root token and port mappings |
| `app/workers/sftp_ingest_worker.py` | Polls SFTP every 5s → validates TIFF → creates batch → uploads to MinIO → pushes Redis job |
| `app/infra/blob/minio_client.py` | `upload_bytes`, `download_bytes`, `delete_file` against MinIO |
| `app/infra/queue/rq_queue.py` | `enqueue_job` — pushes inference jobs into the Redis RQ queue |
| `app/infra/queue/redis_client.py` | Redis connection setup |
| `app/infra/cache/redis_cache.py` | Redis connection used by `cache_service` for fastapi-cache2 |
| `app/infra/sftp/watcher.py` | Lists, downloads, and moves files on the SFTP server |
| `app/infra/vault/vault_client.py` | `get_secret(path)` — fetches secrets from Vault KV v2 at startup |
| `app/infra/logging/logger.py` | Structured JSON logger, carries `request_id` across api, queue, and worker |
| `app/core/config.py` | All configuration read from environment variables with sensible local defaults |
| `app/core/startup.py` | Health checks at boot: Vault reachable, Redis reachable, MinIO reachable, SHA-256 valid, Casbin populated |
| `alembic.ini` | Alembic configuration file |
| `scripts/bootstrap.sh` | Vault init, secret seeding, MinIO bucket creation |
| `.github/workflows/ci.yml` | CI pipeline: compile check, golden replay test, smoke tests on every push |

---

## The Layering Rule

```
HTTP Request
      │
      ▼
app/api/routers/        ← HTTP only. No SQL. No cache. No external systems.
      │
      ▼
app/services/           ← Business logic. Transactions. Cache invalidation. Audit logging.
      │
      ▼
app/repositories/       ← Pure SQL only. No HTTP errors. No cache calls.
      │
      ▼
app/db/models.py        ← SQLAlchemy ORM. Imported only by repositories.
      │
      ▼
PostgreSQL
```

**Side channels — only from the layer shown:**

```
app/services/     ──▶  app/infra/cache/    ──▶  Redis      (cache invalidation)
app/workers/      ──▶  app/infra/blob/     ──▶  MinIO      (TIFF + overlay storage)
app/workers/      ──▶  app/infra/queue/    ──▶  Redis RQ   (job queue)
app/core/startup  ──▶  app/infra/vault/    ──▶  Vault      (secrets at startup only)
```
