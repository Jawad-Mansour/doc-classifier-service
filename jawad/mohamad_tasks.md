# Mohamad — Complete Task Reference
> Role: Backend + DB + Services (System Spine)
> Branch: feature/mohamad-backend-db
> Golden rule: Repositories = SQL only. Services = business logic.

---

## Task List (build order)

| # | File | Status |
|---|---|---|
| 1 | app/db/base.py | todo |
| 2 | app/core/constants.py | todo |
| 3 | app/exceptions.py | todo |
| 4 | app/db/models.py | todo |
| 5 | app/db/session.py | todo |
| 6 | alembic.ini + alembic/env.py | todo |
| 7 | First Alembic migration | todo |
| 8 | app/domain/user.py | todo |
| 9 | app/domain/batch.py | todo |
| 10 | app/domain/document.py | todo |
| 11 | app/domain/prediction.py | todo |
| 12 | app/domain/audit.py | todo |
| 13 | app/repositories/user_repository.py | todo |
| 14 | app/repositories/batch_repository.py | todo |
| 15 | app/repositories/document_repository.py | todo |
| 16 | app/repositories/prediction_repository.py | todo |
| 17 | app/repositories/audit_repository.py | todo |
| 18 | app/services/audit_service.py | todo |
| 19 | app/services/cache_service.py | todo |
| 20 | app/services/batch_service.py | todo |
| 21 | app/services/prediction_service.py | todo |
| 22 | app/services/user_service.py | todo |
| 23 | tests/services/ | todo |

---

## Task 1 — `app/db/base.py`

**What it is:**
One class — the SQLAlchemy declarative base. Every ORM model inherits from it.
Alembic also reads its metadata to auto-generate migrations.

**Why it matters:**
Nothing in models.py can exist without it. It is the first file in the entire DB layer.

**Approach:**
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```
That is literally all it needs to be.

**Relation to other tasks:**
- Task 4 (models.py) imports Base from here
- Task 6 (alembic/env.py) imports Base.metadata from here

---

## Task 2 — `app/core/constants.py`

**What it is:**
Shared values used across models, services, and tests.

**Why it matters:**
If the confidence threshold or class names are hardcoded in multiple places, they will diverge.
One source of truth here prevents that.

**Approach:**
```python
from enum import Enum

CONFIDENCE_THRESHOLD = 0.7

CLASS_NAMES = [
    "letter", "form", "email", "handwritten", "advertisement",
    "scientific_report", "scientific_publication", "specification",
    "file_folder", "news_article", "budget", "invoice",
    "presentation", "questionnaire", "resume", "memo",
]

class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
```

**Relation to other tasks:**
- Task 4 (models.py) uses BatchStatus for the batch status column
- Task 9 (domain/batch.py) uses BatchStatus
- Task 21 (prediction_service) uses CONFIDENCE_THRESHOLD in relabel guard

---

## Task 3 — `app/exceptions.py`

**What it is:**
Custom exception classes for your layer. Services raise these.
Ali's routers catch them and return the correct HTTP status.

**Why it matters:**
Without these, every error becomes a 500. With them, Ali maps them cleanly:
LastAdminError → 400, UserNotFound → 404, UnauthorizedRelabel → 403.

**Approach:**
```python
class UserNotFound(Exception): pass
class BatchNotFound(Exception): pass
class DocumentNotFound(Exception): pass
class PredictionNotFound(Exception): pass
class LastAdminError(Exception): pass
class UnauthorizedRelabel(Exception): pass
```
Plain exception subclasses. No logic inside them.

**Relation to other tasks:**
- Task 22 (user_service) raises LastAdminError
- Task 21 (prediction_service) raises UnauthorizedRelabel
- Ali's routers (not your code) catch all of these

---

## Task 4 — `app/db/models.py`

**What it is:**
Six SQLAlchemy ORM classes — the database schema in Python.

**Why it matters:**
This defines every column in every table. Get it wrong and every migration,
repository, and service breaks. Imported ONLY by repositories.

**The 6 tables:**

```
User         — id, email, hashed_password, role, created_at
Batch        — id, request_id, status (BatchStatus), created_at
Document     — id, batch_id (FK→Batch), filename, blob_bucket, blob_path, created_at
Prediction   — id, document_id (FK→Document), batch_id (FK→Batch),
               label_id, label, confidence,
               top5 (JSON), all_probs (JSON),
               model_sha256, overlay_bucket, overlay_path,
               relabeled_by, created_at
AuditLog     — id, actor, action, target, timestamp
CasbinRule   — id, ptype, v0, v1, v2
```

Note: Document table is NOT listed in tasks.pdf but IS required because:
- Aya calls add_document() which must persist somewhere
- Redis job payload has document_id: 44 — that ID must reference a real row

**Approach:**
Use SQLAlchemy 2.x mapped_column style. Keep it flat — no complex relationships needed,
just foreign keys with Integer columns.

**Relation to other tasks:**
- Task 1 (base.py) — all models inherit from Base
- Task 2 (constants.py) — BatchStatus used in Batch.status column
- Tasks 13-17 (repositories) — only place that imports from models.py
- Task 6 (alembic) — reads models via Base.metadata to generate migrations

---

## Task 5 — `app/db/session.py`

**What it is:**
Creates the async SQLAlchemy engine and exposes a session factory.
Every repository receives a session from here.

**Why it matters:**
Without a session, no repository function can run a query.
This is the DB connection pipeline for the entire app.

**Approach:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```
Read DATABASE_URL from environment. Keep it simple — no pool tuning needed yet.

**Relation to other tasks:**
- Task 4 (models.py) — engine connects to the DB that models describe
- Tasks 13-17 (repositories) — all take `session` as a parameter, session comes from here
- Ali's deps/auth.py — will inject get_session as a FastAPI dependency

---

## Task 6 — `alembic.ini` + `alembic/env.py`

**What it is:**
Configuration that tells Alembic where migrations live and how to connect to the DB.
env.py imports your Base.metadata so Alembic can compare models to DB state.

**Why it matters:**
Without this, `alembic revision --autogenerate` cannot produce a migration.
Without migrations, the `migrate` Docker container has nothing to run.

**Approach:**
- alembic.ini: point `script_location` at `alembic/`, set `sqlalchemy.url` from env var
- env.py: import `Base` from `app.db.base`, set `target_metadata = Base.metadata`

**Relation to other tasks:**
- Task 1 (base.py) — env.py imports Base from here
- Task 7 (migration) — this config makes the migration possible

---

## Task 7 — First Alembic Migration

**What it is:**
Auto-generated Python file with upgrade() and downgrade() functions.
Running `alembic upgrade head` creates all 6 tables in Postgres.

**Why it matters:**
The `migrate` Docker container runs this before the API boots.
Without it, the database is empty and the entire system fails at startup.

**Approach:**
After tasks 1-6 are done, run:
```
alembic revision --autogenerate -m "initial"
alembic upgrade head
```
Review the generated file — make sure all 6 tables appear. Fix any column types if needed.

**Relation to other tasks:**
- Task 4 (models.py) — migration is generated from these models
- Task 6 (alembic config) — config must be correct before this runs
- Aya's docker-compose — migrate container runs this command on startup

---

## Task 8 — `app/domain/user.py`

**What it is:**
Pydantic model representing a user as it leaves your layer.

**Why it matters:**
Ali's routers receive UserDomain, not a SQLAlchemy row.
This prevents hashed_password and ORM internals from leaking into API responses.

**Fields:** id, email, role, created_at
(no hashed_password — never expose this)

**Relation to other tasks:**
- Task 22 (user_service) — register_user and toggle_role return UserDomain
- Ali's schemas — Ali wraps UserDomain in his own response schema

---

## Task 9 — `app/domain/batch.py`

**What it is:**
Pydantic model for a batch.

**Fields:** id, request_id, status (BatchStatus), created_at

**Relation to other tasks:**
- Task 20 (batch_service) — create_batch, get_batch, list_batches all return BatchDomain
- Ali's GET /batches and GET /batches/{bid} — receive BatchDomain from your service

---

## Task 10 — `app/domain/document.py`

**What it is:**
Pydantic model for a document within a batch.

**Fields:** id, batch_id, filename, blob_bucket, blob_path, created_at

**Why it matters:**
Aya calls add_document() and needs document.id back to put in the Redis job payload.
Without this domain model, Aya has no typed return value to work with.

**Relation to other tasks:**
- Task 20 (batch_service.add_document) — returns DocumentDomain
- Aya's sftp_ingest_worker — reads document.id from the returned DocumentDomain

---

## Task 11 — `app/domain/prediction.py`

**What it is:**
Pydantic model for a prediction. Must match exactly what Jad sends to create_prediction().

**Fields:**
id, document_id, batch_id, label_id, label, confidence,
top5 (list of {label_id, label, confidence}),
all_probs (dict label→float),
model_sha256, overlay_bucket, overlay_path,
relabeled_by (nullable), created_at

**Why it matters:**
Jad's inference_worker calls create_prediction() with these exact fields.
Ali's GET /predictions/recent returns a list of PredictionDomain.
If the shape is wrong, both Jad and Ali break.

**Relation to other tasks:**
- Task 21 (prediction_service) — all prediction functions return PredictionDomain
- Jad's inference_worker — caller of create_prediction, shapes must match
- Ali's GET /predictions/recent and list_predictions — receives PredictionDomain

---

## Task 12 — `app/domain/audit.py`

**What it is:**
Pydantic model for an audit log entry.

**Fields:** id, actor, action, target, timestamp

**Relation to other tasks:**
- Task 18 (audit_service.list_logs) — returns list of AuditEntryDomain
- Ali's GET /audit-log — receives list of AuditEntryDomain

---

## Task 13 — `app/repositories/user_repository.py`

**What it is:**
SQL queries for users. Four functions, no logic.

**Functions:**
- get_by_id(session, user_id)
- get_by_email(session, email)
- create(session, email, hashed_password, role)
- update_role(session, user_id, new_role)

**Rules:** No HTTP exceptions. No admin count checks. No cache calls. SQL only.

**Relation to other tasks:**
- Task 22 (user_service) — calls these functions, applies the logic around them

---

## Task 14 — `app/repositories/batch_repository.py`

**What it is:**
SQL queries for batches. Four functions, no logic.

**Functions:**
- create(session, request_id) → returns new Batch row
- get_by_id(session, batch_id)
- list_all(session)
- update_status(session, batch_id, status)

**Relation to other tasks:**
- Task 20 (batch_service) — calls these, adds audit + cache around them

---

## Task 15 — `app/repositories/document_repository.py`

**What it is:**
SQL queries for documents. Two functions.

**Functions:**
- create(session, batch_id, filename, blob_bucket, blob_path) → returns new Document row with id
- get_by_id(session, document_id)

**Why it matters:**
The returned document.id from create() is what Aya puts into the Redis job payload.
If this is wrong, Jad receives an invalid document_id.

**Relation to other tasks:**
- Task 20 (batch_service.add_document) — calls document_repo.create()
- Aya's sftp_ingest_worker — depends on document.id being returned correctly

---

## Task 16 — `app/repositories/prediction_repository.py`

**What it is:**
SQL queries for predictions. Four functions.

**Functions:**
- create(session, all fields from Jad's contract)
- get_by_batch(session, batch_id)
- get_recent(session, limit)
- update_label(session, prediction_id, new_label, relabeled_by)

**Relation to other tasks:**
- Task 21 (prediction_service) — calls these, applies confidence guard and audit around them

---

## Task 17 — `app/repositories/audit_repository.py`

**What it is:**
SQL queries for audit log. Three functions.

**Functions:**
- create(session, actor, action, target)
- list_all(session)
- list_by_actor(session, actor)

**Relation to other tasks:**
- Task 18 (audit_service) — only caller of these functions

---

## Task 18 — `app/services/audit_service.py`

**What it is:**
Service for audit logging. Two functions.

**Functions:**
- log_event(session, actor, action, target) — writes an audit row
- list_logs(session) — returns list of AuditEntryDomain

**Why it matters:**
project-6.pdf requires audit entries for every role change, relabel, AND batch state change.
This service is called from user_service, prediction_service, and batch_service.
It is never called from a router.

**Relation to other tasks:**
- Task 17 (audit_repository) — all calls go through here
- Tasks 20, 21, 22 (batch/prediction/user services) — all call log_event()
- Ali's GET /audit-log — calls list_logs()

---

## Task 19 — `app/services/cache_service.py`

**What it is:**
Wraps Aya's Redis cache adapter. Three functions.

**Functions:**
- invalidate_batch(batch_id) — clears cached GET /batches/{bid}
- invalidate_user(user_id) — clears cached GET /me
- invalidate_predictions() — clears cached GET /predictions/recent

**Why it matters:**
project-6.pdf says invalidation lives in the service layer only.
Routers must never invalidate. Repositories must never invalidate.
Only services call this.

**Approach:**
Call Aya's redis_cache.invalidate(key) with the correct cache key format.
Agree the key format with Ali (he sets the cache, you clear it).

**Relation to other tasks:**
- Aya's infra/cache/redis_cache.py — the underlying adapter you wrap
- Tasks 20, 21, 22 — all call cache_service after writes

---

## Task 20 — `app/services/batch_service.py`

**What it is:**
Business logic for batches. Five functions. This is the first service Aya depends on.

**Functions:**
- create_batch(session, request_id) → BatchDomain
  Creates batch with status=pending. No guard needed.

- add_document(session, batch_id, filename, blob_bucket, blob_path) → DocumentDomain
  Inserts document row. Returns DocumentDomain with id.
  Aya reads document.id and puts it in the Redis job.

- get_batch(session, batch_id) → BatchDomain
  Simple read. Check cache first (Aya/Ali wire this up).

- list_batches(session) → list[BatchDomain]
  Simple read.

- update_status(session, batch_id, status) → BatchDomain
  Updates status.
  Calls audit_service.log_event() — required by project-6.pdf.
  Calls cache_service.invalidate_batch(batch_id).

**Who calls this:**
- Aya: create_batch() and add_document() before pushing Redis job
- Jad: update_status() after inference completes
- Ali: get_batch() and list_batches() for API endpoints

**Relation to other tasks:**
- Tasks 14, 15 (batch_repo, document_repo) — called internally
- Tasks 18, 19 (audit, cache services) — called after writes
- Tasks 9, 10 (domain models) — return types

---

## Task 21 — `app/services/prediction_service.py`

**What it is:**
Business logic for predictions. Four functions. Jad is blocked on this.

**Functions:**
- create_prediction(session, job_id, batch_id, document_id, label_id, label,
  confidence, top5, all_probs, model_sha256, overlay_bucket, overlay_path, request_id)
  Saves prediction row.
  Calls audit_service.log_event().
  Calls cache_service.invalidate_predictions().

- list_predictions(session, batch_id) → list[PredictionDomain]
  Returns all predictions for a batch. Ali calls this for GET /batches/{bid}.

- get_recent(session, limit) → list[PredictionDomain]
  Returns most recent N predictions. Ali calls this for GET /predictions/recent.

- relabel(session, prediction_id, new_label, reviewer_user)
  GUARD: if prediction.confidence >= CONFIDENCE_THRESHOLD → raise UnauthorizedRelabel
  If allowed: update label, call audit_service.log_event(), call cache_service.invalidate_predictions().

**Who calls this:**
- Jad: create_prediction() from inference_worker after model runs
- Ali: list_predictions(), get_recent(), relabel() from routers

**Relation to other tasks:**
- Task 16 (prediction_repo) — called internally
- Tasks 18, 19 (audit, cache) — called after every write
- Task 3 (exceptions) — raises UnauthorizedRelabel
- Task 2 (constants) — reads CONFIDENCE_THRESHOLD

---

## Task 22 — `app/services/user_service.py`

**What it is:**
Business logic for users. Two functions.

**Functions:**
- register_user(session, email, password) → UserDomain
  Hashes password using Ali's security.py hash function.
  Calls user_repo.create(). Returns UserDomain.

- toggle_role(session, user_id, new_role, actor) → UserDomain
  GUARD: count users with role=admin.
  If count == 1 and this user is that admin → raise LastAdminError.
  Otherwise: call user_repo.update_role().
  Call audit_service.log_event().
  Call cache_service.invalidate_user(user_id).

**Who calls this:**
- Ali: register_user() at POST /auth/register
- Ali: toggle_role() at PATCH /admin/users/{id}/role

**Relation to other tasks:**
- Task 13 (user_repo) — called internally
- Tasks 18, 19 (audit, cache) — called after writes
- Task 3 (exceptions) — raises LastAdminError
- Ali's security.py — provides the password hashing function (you call it, Ali owns it)

---

## Task 23 — `tests/services/`

**What it is:**
Unit tests for all service business rules. No real DB needed — use mocked repositories.

**Key tests to write:**
- toggle_role raises LastAdminError when last admin demotes themselves
- toggle_role succeeds when there are 2+ admins
- relabel raises UnauthorizedRelabel when confidence >= 0.7
- relabel succeeds when confidence < 0.7
- create_prediction calls cache_service.invalidate_predictions() after save
- create_prediction calls audit_service.log_event() after save
- update_status calls audit_service.log_event() after every change
- add_document returns a DocumentDomain with a valid id

**Approach:**
Use pytest + unittest.mock. Create a fake session and fake repository that returns
controlled test data. Pass these into the service functions. Assert the output and
that the right side-effect calls were made.

**Relation to other tasks:**
- All services (tasks 20-22) — what you are testing
- Does NOT require tasks 1-7 (no real DB needed for service tests)

---

## How They All Connect — The Flow

```
FOUNDATION (tasks 1-7)
base.py → models.py → session.py → alembic config → migration
Result: 6 empty tables in Postgres

CONTRACTS (tasks 8-12)
domain models: User, Batch, Document, Prediction, AuditLog
Result: Ali and Jad know the data shapes — they can start coding

SHARED VALUES (tasks 2, 3)
constants.py → CONFIDENCE_THRESHOLD, BatchStatus, CLASS_NAMES
exceptions.py → LastAdminError, UnauthorizedRelabel, etc.

SQL LAYER (tasks 13-17)
user_repo, batch_repo, document_repo, prediction_repo, audit_repo
Rule: SQL in, domain model out. No logic here.

SUPPORT SERVICES (tasks 18-19)
audit_service → called by all other services after writes
cache_service → called by all other services after writes

BUSINESS SERVICES (tasks 20-22)
batch_service   → unblocks Aya (create_batch, add_document)
prediction_service → unblocks Jad (create_prediction)
user_service    → unblocks Ali (toggle_role)

TESTS (task 23)
Proves business rules work without a real DB
```

---

## Live Request Trace

```
[AYA] SFTP picks up file1.tiff
  → batch_service.create_batch(request_id)
      → batch_repo.create()
      ← BatchDomain(id=12)
  → batch_service.add_document(batch_id=12, filename, bucket, path)
      → document_repo.create()
      ← DocumentDomain(id=44)
  → push Redis job: {batch_id:12, document_id:44, ...}

[JAD] inference_worker dequeues job
  → downloads TIFF, runs model → label, confidence, top5, all_probs
  → prediction_service.create_prediction(batch_id=12, document_id=44, ...)
      → prediction_repo.create()
      → audit_service.log_event("system", "prediction_created", "doc_44")
      → cache_service.invalidate_predictions()
  → batch_service.update_status(12, "done")
      → batch_repo.update_status()
      → audit_service.log_event("system", "status_change", "batch_12")
      → cache_service.invalidate_batch(12)

[ALI] GET /batches/12
  → batch_service.get_batch(12) → BatchDomain
  → prediction_service.list_predictions(12) → list[PredictionDomain]

[ALI] PATCH /predictions/55 (reviewer relabels)
  → prediction_service.relabel(55, "form", reviewer)
      GUARD: confidence >= 0.7 → raise UnauthorizedRelabel → Ali returns 403
      OR if confidence < 0.7:
      → prediction_repo.update_label()
      → audit_service.log_event(reviewer, "relabel", "prediction_55")
      → cache_service.invalidate_predictions()

[ALI] PATCH /admin/users/7/role
  → user_service.toggle_role(7, "auditor", admin)
      GUARD: count admins == 1 → raise LastAdminError → Ali returns 400
      OR if safe:
      → user_repo.update_role()
      → audit_service.log_event(admin, "role_change", "user_7")
      → cache_service.invalidate_user(7)
```

---

## Contracts You Must Satisfy

### Aya calls you:
```python
batch = batch_service.create_batch(request_id="uuid-abc-123")
document = batch_service.add_document(
    batch_id=batch.id,
    filename="file1.tiff",
    blob_bucket="documents",
    blob_path="raw/batch_12/file1.tiff",
)
# Aya then uses batch.id and document.id in the Redis job
```

### Jad calls you:
```python
prediction_service.create_prediction(
    job_id="uuid",
    batch_id=12,
    document_id=44,
    label_id=11,
    label="invoice",
    confidence=0.93,
    top5=[{"label_id": 11, "label": "invoice", "confidence": 0.93}, ...],
    all_probs={"invoice": 0.93, "budget": 0.04, ...},
    model_sha256="dc3737d3584d8ba8a405041cd97486835f15a56d3914914247d0b4002d1d4bb5",
    overlay_bucket="documents",
    overlay_path="overlays/batch_12/file1_overlay.png",
    request_id="uuid-abc-123",
)
```

### Ali calls you:
```python
prediction_service.list_predictions(batch_id)
batch_service.list_batches()
batch_service.get_batch(batch_id)
audit_service.list_logs()
user_service.toggle_role(user_id, new_role, actor)
user_service.register_user(email, password)
```
