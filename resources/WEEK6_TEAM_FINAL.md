# Week 6 — Document Classifier as an Authenticated Service
## Final Team Plan (All fixes applied, Trello-ready)

> Original assignments preserved. Additions marked ★.
> Use this file as the source of truth for Trello cards.

---

## Team Ownership

| Person  | Main Role                             | Owns                                                                   |
|---------|---------------------------------------|------------------------------------------------------------------------|
| Jad     | ML + Inference                        | model, inference logic, inference_worker.py, golden tests, LICENSES.md |
| Ali     | API + Auth + Permissions              | routers, JWT, Casbin, schemas, API responses, seed_policies.py         |
| Mohamad | Backend Architecture + DB + Services  | SQLAlchemy, Alembic, repositories, services, audit/cache logic         |
| Aya     | Infrastructure + DevOps + Reliability | Docker, Redis, MinIO, SFTP, Vault, CI/CD, sftp_ingest_worker.py        |

---

## Full Workflow (with owners)

```
Scanner uploads TIFF
        ↓
SFTP Server                              ← Aya
        ↓
SFTP-Ingest Worker                       ← Aya
        ↓
★ Creates batch via batch_service        ← Aya calls Mohamad's service
        ↓
Uploads TIFF to MinIO                    ← Aya
        ↓
Pushes Redis job                         ← Aya
  { batch_id, blob_path,
    original_filename, request_id ★ }
        ↓
Inference Worker consumes job            ← Jad
        ↓
Model predicts label / confidence        ← Jad
        ↓
Prediction saved via service             ← Jad calls Mohamad's service
  { batch_id, label, confidence,
    top5 ★, all_probs ★, overlay_path }
        ↓
Cache invalidated + audit logged         ← Mohamad
        ↓
API exposes predictions                  ← Ali
        ↓
JWT + Casbin permissions checked         ← Ali
        ↓
Authenticated users view results
```

**Key rule:**
```
Ali routes      → Mohamad services → Mohamad repositories → database
Jad worker      → Mohamad services → database
Aya ingest      → Mohamad batch_service (create batch) → Redis job → Jad worker ★
```

---

## Contracts (agree before writing any code)

### Contract 1 — Aya → Jad (RQ job payload)
```json
{
  "batch_id": 12,
  "blob_path": "raw/file1.tiff",
  "original_filename": "file1.tiff",
  "request_id": "uuid-abc-123"
}
```
★ `request_id` added — required for end-to-end log tracing across api, queue, worker.

### Contract 2 — Jad → Mohamad (prediction result)
```json
{
  "batch_id": 12,
  "label": "invoice",
  "confidence": 0.93,
  "top5": [["invoice",0.93],["budget",0.04],["form",0.01],["letter",0.01],["memo",0.01]],
  "all_probs": {"invoice":0.93,"budget":0.04,"form":0.01,"letter":0.01,"memo":0.01},
  "overlay_path": "overlays/batch_12/file1_overlay.png"
}
```
★ `top5` and `all_probs` added — required for model card metrics and prediction storage.

### Contract 3 — Mohamad → Ali (service interface)
```python
prediction_service.list_predictions(batch_id)
batch_service.list_batches()
batch_service.get_batch(batch_id)
audit_service.list_logs()
```

### ★ Contract 4 — Aya → Mohamad (batch creation — was missing)
```python
# Aya calls this in sftp_ingest_worker.py BEFORE pushing the Redis job
batch = batch_service.create_batch(filename="file1.tiff", request_id="uuid-abc-123")
# batch.id is then put into the RQ job payload
```

---

## Project Structure (full, with owners)

```
project-root/
│
├── app/
│   ├── api/                              ← ALI
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── batches.py
│   │   │   ├── predictions.py
│   │   │   └── audit.py
│   │   ├── deps/
│   │   │   ├── auth.py
│   │   │   ├── permissions.py
│   │   │   └── cache.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── batch.py
│   │   │   ├── prediction.py
│   │   │   └── user.py
│   │   └── middleware/
│   │       └── request_id.py
│   │
│   ├── auth/                             ← ALI
│   │   ├── jwt.py
│   │   ├── users.py
│   │   └── casbin.py
│   │
│   ├── services/                         ← MOHAMAD
│   │   ├── batch_service.py
│   │   ├── prediction_service.py
│   │   ├── user_service.py
│   │   ├── audit_service.py
│   │   └── cache_service.py
│   │
│   ├── repositories/                     ← MOHAMAD
│   │   ├── user_repository.py
│   │   ├── batch_repository.py
│   │   ├── prediction_repository.py
│   │   └── audit_repository.py
│   │
│   ├── domain/                           ← MOHAMAD
│   │   ├── user.py
│   │   ├── batch.py
│   │   ├── prediction.py
│   │   └── audit.py
│   │
│   ├── db/                               ← MOHAMAD
│   │   ├── models.py
│   │   ├── session.py
│   │   ├── base.py
│   │   └── migrations/
│   │
│   ├── classifier/                       ← JAD
│   │   ├── inference/
│   │   │   ├── predictor.py
│   │   │   ├── preprocessing.py          ★ single source of truth for transforms
│   │   │   ├── postprocessing.py
│   │   │   └── overlays.py
│   │   ├── models/
│   │   │   ├── classifier.pt             (git LFS)
│   │   │   ├── model_card.json
│   │   │   └── labels.json
│   │   ├── eval/
│   │   │   ├── golden.py
│   │   │   ├── golden_expected.json
│   │   │   └── golden_images/
│   │   └── training/
│   │       └── train_colab.ipynb
│   │
│   ├── workers/
│   │   ├── inference_worker.py           ← JAD
│   │   └── sftp_ingest_worker.py         ← AYA
│   │
│   ├── infra/                            ← AYA
│   │   ├── blob/
│   │   │   └── minio_client.py
│   │   ├── queue/
│   │   │   ├── redis_client.py
│   │   │   └── rq_queue.py
│   │   ├── cache/
│   │   │   └── redis_cache.py
│   │   ├── vault/
│   │   │   └── vault_client.py
│   │   ├── sftp/
│   │   │   └── watcher.py
│   │   └── logging/
│   │       └── logger.py
│   │
│   ├── core/
│   │   ├── config.py                     ← AYA
│   │   ├── startup.py                    ← AYA + JAD + ALI (see split below)
│   │   ├── security.py                   ← ALI
│   │   └── constants.py                  ← MOHAMAD
│   │
│   ├── main.py                           ← ALI
│   └── exceptions.py                     ← MOHAMAD
│
├── tests/
│   ├── api/                              ← ALI
│   ├── services/                         ← MOHAMAD
│   ├── classifier/                       ← JAD
│   ├── infra/                            ← AYA
│   └── smoke/                            ← AYA
│
├── .github/
│   └── workflows/
│       └── ci.yml                        ← AYA
│
├── docker/
│   ├── api.Dockerfile                    ← AYA
│   ├── worker.Dockerfile                 ← AYA
│   └── ingest.Dockerfile                 ← AYA
│
├── alembic.ini                           ← MOHAMAD
├── docker-compose.yml                    ← AYA
├── requirements.txt                      ← ALL
├── .env.example                          ← AYA
├── pyproject.toml                        ← AYA
├── README.md                             ← ALL
├── ARCH.md                               ← ALL
├── DECISIONS.md                          ← ALL
├── RUNBOOK.md                            ← AYA
├── SECURITY.md                           ← ALI + AYA
├── COLLABORATION.md                      ← ALL
├── LICENSES.md                           ← JAD
└── scripts/
    ├── bootstrap.sh                      ← AYA
    └── seed_policies.py                  ← ALI
```

---

## ★ startup.py — Responsibility Split

Each person writes only their own checks. Do not mix them.

| Check | Owner | What it verifies |
|---|---|---|
| 1. classifier.pt exists | Jad | File present at expected path |
| 2. SHA-256 matches model_card.json | Jad | Weights not corrupted or swapped |
| 3. model_card top-1 >= README threshold | Jad | Bad model not deployed |
| 4. Vault reachable + returns JWT key | Aya | Secrets available |
| 5. Redis reachable | Aya | Queue and cache available |
| 6. MinIO reachable | Aya | Blob storage available |
| 7. ★ Casbin policy table not empty | Ali | Permissions defined before serving traffic |

---

## ★ Latency Measurement — Assigned

| Measurement | Owner | Target |
|---|---|---|
| API cached reads p95 | Aya | < 50ms |
| API uncached reads p95 | Aya | < 200ms |
| Inference per document p95 | Jad | < 1.0s (CPU) |
| End-to-end SFTP drop → API p95 | Aya | < 10s |
| Write all numbers into README | Aya | Before submission |

---

## Integration Order

```
Step 1: Aya     → docker-compose up, all 9 containers healthy
Step 2: Mohamad → DB migrations run, services testable with mocks
Step 3: Jad     → inference worker connects to Redis + MinIO
Step 4: Jad     → saves prediction through Mohamad's service
Step 5: Ali     → routers connect to Mohamad's services
Step 6: ALL     → full smoke test: TIFF drop → prediction visible in API
```

---

## Working Method

### Branches
```
main
dev
feature/jad-ml
feature/ali-api-auth
feature/mohamad-backend-db
feature/aya-infra
```
Feature branch → PR to dev → reviewed by one teammate → merge.

### Work independently with mocks
```
Jad     → tests ML with a fake RQ job payload
Ali     → builds API with fake service return values
Mohamad → builds services with fake prediction input data
Aya     → builds all infra containers standalone
```

### PR rules (before any merge)
- Code runs locally
- No secrets committed
- No broken imports
- Tests pass
- One teammate reviewed

---

## Trello Cards — Per Person

### JAD
| Card | Description |
|---|---|
| Colab training notebook | train_colab.ipynb — ConvNeXt Tiny on RVL-CDIP, stratified subset |
| preprocessing.py | Define transforms FIRST — single source of truth, Colab must match |
| predictor.py | Load model once at startup, expose predict(bytes) → dict |
| postprocessing.py | Extract top-1, top-5, all_probs from logits |
| overlays.py | Draw label + confidence on TIFF, return PNG bytes |
| inference_worker.py | Dequeue RQ job, run pipeline, call Mohamad services, log with request_id |
| Model artifacts | classifier.pt (git LFS), model_card.json, labels.json |
| Golden set | Pick 50 images from test split, save golden_expected.json |
| golden.py | CI replay test — byte-identical labels, confidence within 1e-6 |
| startup.py (Jad portion) | SHA-256 check + model threshold check |
| tests/classifier/ | Preprocessing shape test, postprocessing test, golden replay |
| LICENSES.md | Flag RVL-CDIP as academic/research use only |

### ALI
| Card | Description |
|---|---|
| main.py | FastAPI app entry point, register all routers |
| auth/jwt.py | JWT strategy, key injected from Vault at startup |
| auth/users.py | fastapi-users SQLAlchemy adapter setup |
| auth/casbin.py | Casbin SQLAlchemy adapter, policy loader |
| routers/auth.py | POST /auth/register, POST /auth/login |
| routers/users.py | GET /me, PATCH /admin/users/{id}/role |
| routers/batches.py | GET /batches, GET /batches/{bid} |
| routers/predictions.py | GET /predictions/recent, PATCH /predictions/{id} |
| routers/audit.py | GET /audit-log |
| deps/auth.py | get_current_user dependency |
| deps/permissions.py | Casbin enforcement dependency |
| deps/cache.py | Cache decorator wiring |
| middleware/request_id.py | Generate UUID per request, inject into context |
| schemas/ | Pydantic request/response schemas for all endpoints |
| security.py | Password hashing helpers |
| startup.py (Ali portion) | Check Casbin policy table not empty |
| seed_policies.py | Script to insert default Casbin rules into DB |
| tests/api/ | Route tests with mocked services |
| SECURITY.md (Ali portion) | JWT policy, secrets discipline, what to do if key leaks |

### MOHAMAD
| Card | Description |
|---|---|
| db/models.py | SQLAlchemy ORM models: User, Batch, Prediction, AuditLog, CasbinRule |
| db/session.py | Async SQLAlchemy session factory |
| db/base.py | Declarative base |
| alembic.ini | Alembic configuration |
| migrations/ | Initial migration (all tables) + seed Casbin rules + seed admin user |
| domain/user.py | Pydantic UserDomain model |
| domain/batch.py | Pydantic BatchDomain model |
| domain/prediction.py | Pydantic PredictionDomain model (includes top5, all_probs ★) |
| domain/audit.py | Pydantic AuditEntryDomain model |
| repositories/user_repository.py | get_by_id, get_by_email, create, update_role |
| repositories/batch_repository.py | create, get_by_id, list_all, update_status |
| repositories/prediction_repository.py | create, get_by_batch, get_recent, update_label |
| repositories/audit_repository.py | create, list_all, list_by_actor |
| services/user_service.py | register_user, toggle_role (blocks last admin demotion) |
| services/batch_service.py | create_batch ★, get_batch, list_batches, update_status |
| services/prediction_service.py | create_prediction, relabel (confidence < 0.7 guard), get_recent |
| services/audit_service.py | log_event, list_logs |
| services/cache_service.py | invalidate_batch, invalidate_user, invalidate_predictions |
| exceptions.py | Domain exceptions: UserNotFound, BatchNotFound, LastAdminError, etc. |
| constants.py | Class names list, confidence threshold (0.7), status enums |
| tests/services/ | Service unit tests with mocked repositories |

### AYA
| Card | Description |
|---|---|
| docker-compose.yml | All 9 services: vault, db, redis, minio, sftp, migrate, api, worker, sftp-ingest |
| docker/api.Dockerfile | FastAPI app image |
| docker/worker.Dockerfile | Inference worker image |
| docker/ingest.Dockerfile | SFTP ingest worker image |
| .env.example | Vault root token + port mappings only |
| infra/vault/vault_client.py | get_secret(path) — fetch from Vault KV v2 at startup |
| infra/blob/minio_client.py | upload_file, download_file, delete_file |
| infra/queue/redis_client.py | Redis connection setup |
| infra/queue/rq_queue.py | enqueue_job, job status helpers |
| infra/cache/redis_cache.py | get, set, invalidate — used by cache_service |
| infra/sftp/watcher.py | List new files, download, move to processed |
| infra/logging/logger.py | Structured JSON logger, request_id from context |
| sftp_ingest_worker.py | Poll SFTP every 5s, validate, upload MinIO, call batch_service.create_batch ★, enqueue RQ job |
| core/config.py | All config loaded from env / Vault |
| startup.py (Aya portion) | Vault reachable, Redis reachable, MinIO reachable |
| scripts/bootstrap.sh | Vault init + secret seeding, MinIO bucket creation |
| .github/workflows/ci.yml | lint, type-check, build, golden test, smoke test |
| tests/infra/ | Adapter unit tests |
| tests/smoke/ | Full stack smoke test: TIFF → prediction in API |
| RUNBOOK.md | Start, stop, reset, add user, swap model, check logs |
| SECURITY.md (Aya portion) | Vault setup, secret rotation, SFTP permissions |
| ★ Latency measurement | Benchmark API + e2e, record p95 numbers in README |

---

## What Everyone Depends On (build order)

```
Mohamad (domain models + service signatures)
    ↓ Jad and Ali both depend on this to know what to pass and what to call
    ↓
Aya (infra running) + Jad (preprocessing.py defined)
    ↓ both must exist before integration begins
    ↓
Jad connects inference worker to Redis + MinIO + Mohamad services
    ↓
Ali connects routers to Mohamad services
    ↓
Aya wires CI smoke test against full running stack
```

---

## Summary of All Fixes vs Original PDF

| # | Fix | Who it affects |
|---|---|---|
| 1 | Add `request_id` to Aya→Jad RQ job contract | Aya + Jad |
| 2 | Add `top5` + `all_probs` to Jad→Mohamad prediction contract | Jad + Mohamad |
| 3 | Aya must call `batch_service.create_batch()` before enqueue | Aya + Mohamad |
| 4 | `preprocessing.py` = single source of truth; Colab must match exactly | Jad |
| 5 | Casbin startup check (#7 in startup.py) moved to Ali | Ali |
| 6 | Latency measurement formally assigned (API/e2e → Aya, inference → Jad) | Aya + Jad |
