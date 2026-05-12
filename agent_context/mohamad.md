# Mohamad — DB / Services / Repositories

> Branch: `feature/mohamad-backend-db`
> Role: Backend + DB + Services (System Spine)
> Status: All 23 tasks complete. 13/13 unit tests passing.

---

## Introduction — What Mohamad Built and Why

Mohamad owns the entire data layer of the document classifier service. This is the system spine: nothing in the application can run without it. The four teammates divide the work as follows:

- **Jad** — ML model and inference pipeline (produces predictions)
- **Ali** — API routers, authentication middleware, HTTP layer (consumes services)
- **Aya** — Infrastructure, Docker, MinIO, Redis, job queue (calls services to create batches/documents)
- **Mohamad** — everything in between: the database schema, ORM models, repositories, business services, domain contracts, and unit tests

The architecture enforces a strict dependency hierarchy:

```
HTTP request  →  Ali's router
                     ↓
              Mohamad's service        (business logic, transactions, audit, cache)
                     ↓
              Mohamad's repository     (pure SQL, no logic)
                     ↓
              Mohamad's ORM model      (SQLAlchemy table definition)
                     ↓
              PostgreSQL database
```

Nothing skips a layer. Ali never touches a repository. Jad never touches the HTTP layer. Aya never writes SQL. Every other teammate imports from Mohamad's service layer and receives Mohamad's domain models (Pydantic objects) as the return type.

The build order within Mohamad's scope was strictly bottom-up:

```
Step 1 — Foundation:      base.py → models.py → session.py → alembic
Step 2 — Shared values:   constants.py → exceptions.py
Step 3 — Domain models:   user, batch, document, prediction, audit (Pydantic contracts)
Step 4 — Repositories:    user, batch, document, prediction, audit (pure SQL)
Step 5 — Services:        audit_service, cache_service, batch_service, prediction_service, user_service
Step 6 — Tests:           unit tests for all business rules (no real DB needed)
```

---

## Scope

- `app/db/` — ORM base, ORM models, async session factory
- `alembic/` — migration configuration and first migration
- `app/core/constants.py` — CLASS_NAMES, CONFIDENCE_THRESHOLD, BatchStatus, UserRole
- `app/exceptions.py` — 6 signal exception classes
- `app/domain/` — 5 Pydantic domain models (the contracts between services and routers)
- `app/repositories/` — 5 repository modules (pure SQL, no business logic)
- `app/services/` — 5 service modules (business logic, transactions, audit, cache)
- `tests/services/` — 13 unit tests for all business rules
- `app/core/security.py` — password hashing (spec says Ali owns this; written because Ali's stub was empty and user_service needed it)

---

## Completed

All 23 assigned tasks are complete:

| Task | Deliverable | File |
|------|-------------|------|
| 1 | SQLAlchemy declarative base | `app/db/base.py` |
| 2 | Shared constants and enums | `app/core/constants.py` |
| 3 | Exception signal classes | `app/exceptions.py` |
| 4 | ORM models (6 tables) | `app/db/models.py` |
| 5 | Async session factory + dependency | `app/db/session.py` |
| 6 | Alembic configuration | `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` |
| 7 | Initial migration (all 6 tables) | `alembic/versions/0001_initial.py` |
| 8 | User domain model | `app/domain/user.py` |
| 9 | Batch domain model | `app/domain/batch.py` |
| 10 | Document domain model (new file — was missing) | `app/domain/document.py` |
| 11 | Prediction domain model | `app/domain/prediction.py` |
| 12 | AuditLog domain model | `app/domain/audit.py` |
| 13 | User repository (5 functions) | `app/repositories/user_repository.py` |
| 14 | Batch repository (4 functions) | `app/repositories/batch_repository.py` |
| 15 | Document repository (3 functions, new file — was missing) | `app/repositories/document_repository.py` |
| 16 | Prediction repository (5 functions) | `app/repositories/prediction_repository.py` |
| 17 | Audit repository (3 functions) | `app/repositories/audit_repository.py` |
| 18 | Audit service (3 functions) | `app/services/audit_service.py` |
| 19 | Cache service (3 functions) | `app/services/cache_service.py` |
| 20 | Batch service (5 functions) | `app/services/batch_service.py` |
| 21 | Prediction service (4 functions) | `app/services/prediction_service.py` |
| 22 | User service (2 functions) | `app/services/user_service.py` |
| 23 | Unit tests (13 tests, 3 files) | `tests/services/test_*.py` |

---

## Files Changed

### New files created (were not in skeleton)
- `app/domain/document.py` — skeleton was missing this entirely
- `app/repositories/document_repository.py` — skeleton was missing this entirely

### Files written from empty stubs
- `app/db/base.py`
- `app/core/constants.py`
- `app/exceptions.py`
- `app/db/models.py`
- `app/db/session.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/0001_initial.py`
- `app/domain/user.py`
- `app/domain/batch.py`
- `app/domain/prediction.py`
- `app/domain/audit.py`
- `app/repositories/user_repository.py`
- `app/repositories/batch_repository.py`
- `app/repositories/prediction_repository.py`
- `app/repositories/audit_repository.py`
- `app/services/audit_service.py`
- `app/services/cache_service.py`
- `app/services/batch_service.py`
- `app/services/prediction_service.py`
- `app/services/user_service.py`
- `app/core/security.py` — spec assigns this to Ali; written because his stub was empty and user_service depends on it
- `tests/services/test_user_service.py`
- `tests/services/test_prediction_service.py`
- `tests/services/test_batch_service.py`

### Modified files
- `pyproject.toml` — added `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`

---

## How to Test

No Docker, no database, no Redis needed for the unit tests. All external calls are replaced with `AsyncMock`.

```bash
# Run only the service unit tests:
uv run pytest tests/services/ -v

# Run the full test suite (includes Jad's classifier tests):
uv run pytest -v
```

Expected output:
```
tests/services/test_user_service.py::test_toggle_role_raises_last_admin_error_when_last_admin PASSED
tests/services/test_user_service.py::test_toggle_role_raises_user_not_found PASSED
tests/services/test_user_service.py::test_toggle_role_succeeds_when_multiple_admins PASSED
tests/services/test_user_service.py::test_toggle_role_calls_audit_and_cache_on_success PASSED
tests/services/test_prediction_service.py::test_relabel_raises_unauthorized_when_confidence_at_threshold PASSED
tests/services/test_prediction_service.py::test_relabel_raises_unauthorized_when_confidence_above_threshold PASSED
tests/services/test_prediction_service.py::test_relabel_succeeds_when_confidence_below_threshold PASSED
tests/services/test_prediction_service.py::test_relabel_raises_prediction_not_found PASSED
tests/services/test_prediction_service.py::test_relabel_calls_audit_and_cache_on_success PASSED
tests/services/test_prediction_service.py::test_create_prediction_calls_audit_and_cache PASSED
tests/services/test_batch_service.py::test_update_status_raises_batch_not_found PASSED
tests/services/test_batch_service.py::test_update_status_calls_audit_and_cache_on_success PASSED
tests/services/test_batch_service.py::test_add_document_returns_domain_with_populated_id PASSED

13 passed
```

What is NOT unit-tested here (by design):
- Repositories — pure SQL, tested against a real DB in integration tests
- Routers — Ali's responsibility
- Inference pipeline — Jad's `tests/classifier/` covers this
- Cache namespace end-to-end — requires running Redis and Ali's `@cache()` decorators

---

## Blocked

Nothing is blocking Mohamad's code at this point. All 23 tasks are done.

The following items are blocking **other teammates** from integrating with Mohamad's layer:

| Blocker | Who it blocks | Details |
|---------|---------------|---------|
| `asyncpg` not in dependencies | Aya (infra) | The async SQLAlchemy session uses `postgresql+asyncpg://`. Without `asyncpg` installed, `create_async_engine` will fail at import time. |
| `DATABASE_SYNC_URL` not set | Aya (infra) | Alembic's `env.py` reads `DATABASE_SYNC_URL` (psycopg2 sync driver). If it's not set in docker-compose, migrations will not run. |
| `all_probs` missing from `PredictionResult` | Jad (ML) | `prediction_service.create_prediction()` requires `all_probs: dict`. Jad must add this field to his `app/classifier/inference/types.py` output type. |
| Cache namespace strings | Ali (API) | Ali's `@cache()` decorators must use the exact namespace strings defined in `cache_service.py` (see Contracts section). |

---

## Contracts Needed from Teammates

### From Aya (infra → Mohamad's session)

Aya must set these two environment variables in `docker-compose.yml` for every container that imports `app.db`:

```yaml
environment:
  DATABASE_URL: "postgresql+asyncpg://user:password@db:5432/docclassifier"
  DATABASE_SYNC_URL: "postgresql+psycopg2://user:password@db:5432/docclassifier"
```

`DATABASE_URL` drives the async FastAPI application. `DATABASE_SYNC_URL` drives Alembic migrations (which run in a separate one-shot container and cannot use asyncpg).

Aya must also ensure `asyncpg` and `psycopg2-binary` are installed:
```toml
# pyproject.toml dependencies
asyncpg = "*"
psycopg2-binary = "*"
```

### From Jad (ML → Mohamad's prediction service)

Jad's inference worker calls `prediction_service.create_prediction()`. The function signature is:

```python
await prediction_service.create_prediction(
    session,
    job_id: str,          # RQ job ID
    batch_id: int,        # from batch_service.create_batch()
    document_id: int,     # from batch_service.add_document()
    label_id: int,        # index into CLASS_NAMES (e.g. 11 for "invoice")
    label: str,           # CLASS_NAMES[label_id] (e.g. "invoice")
    confidence: float,    # softmax score for the top label (0.0–1.0)
    top5: list,           # list of top-5 {label, confidence} dicts
    all_probs: dict,      # full softmax distribution {label: score} for all 16 classes
    model_sha256: str,    # 64-char hex SHA256 of the model weights file
    overlay_bucket: str,  # MinIO bucket name for the GradCAM overlay image
    overlay_path: str,    # MinIO object key for the GradCAM overlay image
    request_id: str,      # original request UUID passed through the job
)
```

**FLAG: `all_probs` is not currently in Jad's `PredictionResult` type.** He must add `all_probs: dict[str, float]` to `app/classifier/inference/types.py` before his worker can call this function.

`label_id` and `label` must be derived from the same source: `CLASS_NAMES` in `app/core/constants.py`. The exact list order is:
```
0=letter, 1=form, 2=email, 3=handwritten, 4=advertisement, 5=scientific_report,
6=scientific_publication, 7=specification, 8=file_folder, 9=news_article,
10=budget, 11=invoice, 12=presentation, 13=questionnaire, 14=resume, 15=memo
```

### To Ali (Mohamad's services → Ali's routers)

Ali calls Mohamad's services and receives Pydantic domain models. The session is injected via `Depends(get_session)` from `app.db.session`.

```python
from app.db.session import get_session
from app.services import batch_service, prediction_service, user_service, audit_service

# In router:
async def create_batch_endpoint(session: AsyncSession = Depends(get_session)):
    result: BatchDomain = await batch_service.create_batch(session, request_id)
    ...

async def list_recent_predictions(session: AsyncSession = Depends(get_session)):
    result: list[PredictionDomain] = await prediction_service.get_recent(session, limit=20)
    ...

async def toggle_user_role(session: AsyncSession = Depends(get_session)):
    try:
        result: UserDomain = await user_service.toggle_role(session, user_id, new_role, actor_email)
    except LastAdminError:
        raise HTTPException(400, "Cannot demote the last admin")
    except UserNotFound:
        raise HTTPException(404, "User not found")
    ...
```

**Cache namespace contract**: Ali's `@cache()` decorators must use these exact namespace strings so that `cache_service.invalidate_*()` functions clear the correct Redis keys:

| Ali's decorator | Mohamad's invalidation call |
|---|---|
| `@cache(namespace=f"batch:{batch_id}")` | `await cache_service.invalidate_batch(batch_id)` |
| `@cache(namespace=f"user:{user_id}")` | `await cache_service.invalidate_user(user_id)` |
| `@cache(namespace="predictions:recent")` | `await cache_service.invalidate_predictions()` |

**Exception → HTTP status mapping** (Ali catches, Mohamad raises):

| Exception | Suggested HTTP status |
|---|---|
| `UserNotFound` | 404 |
| `BatchNotFound` | 404 |
| `DocumentNotFound` | 404 |
| `PredictionNotFound` | 404 |
| `LastAdminError` | 400 |
| `UnauthorizedRelabel` | 403 |

### From/To Aya (infra → Mohamad → Aya's job queue)

Aya's job submission flow calls two batch_service functions before pushing to Redis:

```python
# Aya's worker setup (before pushing RQ job):
batch: BatchDomain = await batch_service.create_batch(session, request_id=request_uuid)
document: DocumentDomain = await batch_service.add_document(
    session,
    batch_id=batch.id,
    filename=uploaded_filename,
    blob_bucket="documents",
    blob_path=f"raw/batch_{batch.id}/{uploaded_filename}",
)
# Now pass document.id to the RQ job payload — Jad's worker needs it
job = q.enqueue(run_inference, document_id=document.id, batch_id=batch.id, ...)
```

The guarantee: `document.id` is always populated when returned from `add_document()`. The repository does `flush()` + `refresh()` before the service does `commit()`, so the DB-assigned integer `id` is readable from the returned `DocumentDomain` object.

---

## Data Formats

### Input formats received from teammates

**From Aya** (batch/document creation):
```python
# create_batch input
request_id: str  # UUID string, e.g. "550e8400-e29b-41d4-a716-446655440000"

# add_document input
batch_id: int           # from the BatchDomain returned above
filename: str           # original file name, e.g. "invoice.tiff"
blob_bucket: str        # MinIO bucket name, e.g. "documents"
blob_path: str          # MinIO object key, e.g. "raw/batch_12/invoice.tiff"
```

**From Jad** (prediction creation):
```python
# All 13 fields for create_prediction — see Contracts section above
# Critical: all_probs must be a dict with ALL 16 class names as keys
all_probs = {
    "letter": 0.01, "form": 0.01, "email": 0.01, "handwritten": 0.01,
    "advertisement": 0.01, "scientific_report": 0.01, "scientific_publication": 0.01,
    "specification": 0.01, "file_folder": 0.01, "news_article": 0.01,
    "budget": 0.04, "invoice": 0.93, "presentation": 0.01, "questionnaire": 0.01,
    "resume": 0.01, "memo": 0.01,
}
```

### Output formats returned to teammates

**To Aya** — `BatchDomain`:
```python
class BatchDomain(BaseModel):
    id: int           # DB-assigned integer primary key
    request_id: str   # the UUID passed in
    status: str       # "pending" | "processing" | "done" | "failed"
    created_at: datetime
```

**To Aya** — `DocumentDomain`:
```python
class DocumentDomain(BaseModel):
    id: int           # DB-assigned integer primary key — CRITICAL for job payload
    batch_id: int
    filename: str
    blob_bucket: str
    blob_path: str
    created_at: datetime
```

**To Ali** — `PredictionDomain`:
```python
class PredictionDomain(BaseModel):
    id: int
    job_id: str
    batch_id: int
    document_id: int
    label_id: int          # 0–15, index into CLASS_NAMES
    label: str             # "invoice", "letter", etc.
    confidence: float      # 0.0–1.0
    top5: list[Any]        # top-5 predictions from Jad's model
    all_probs: dict[str, Any]  # full softmax distribution
    model_sha256: str      # which model ran this prediction
    overlay_bucket: str    # MinIO bucket for GradCAM image
    overlay_path: str      # MinIO key for GradCAM image
    relabeled_by: str | None  # None = model result, email = human override
    request_id: str
    created_at: datetime
```

**To Ali** — `UserDomain`:
```python
class UserDomain(BaseModel):
    id: int
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    role: str   # "admin" | "reviewer" | "auditor"
    # NOTE: hashed_password is intentionally EXCLUDED
```

**To Ali** — `AuditLogDomain`:
```python
class AuditLogDomain(BaseModel):
    id: int
    actor: str       # user email or "system"
    action: str      # "relabel" | "status_change" | "role_change" | "prediction_created"
    target: str      # "type:id" format, e.g. "prediction:42", "batch:12", "user:3"
    timestamp: datetime
```

---

## Caveats / Known Limitations

### 1. `expire_on_commit=False` is required
The async session is configured with `expire_on_commit=False`. Without this, accessing any attribute on an ORM object after `session.commit()` raises `DetachedInstanceError` because SQLAlchemy marks all objects as expired and the async session cannot re-query them lazily. This setting must never be removed.

### 2. `flush()` in repositories, `commit()` in services
Write operations in repositories call `session.flush()` (sends SQL within the open transaction) followed by `session.refresh(obj)` (reads back server-generated values like `id` and `created_at`). The transaction is not committed. Services call `session.commit()`. This pattern means if a service does multiple repository writes, they are all committed atomically. If any single write fails, the entire transaction rolls back.

### 3. Cache invalidation is after commit — order matters
Cache invalidation (`cache_service.invalidate_*()`) always happens after `session.commit()`. If we cleared the cache before committing and the commit failed, the next request would fetch fresh data from the DB and re-cache it — that is correct behavior. If we cleared after committing (our approach) and the invalidation fails, the cache serves stale data temporarily — which is acceptable. If we committed first and invalidation raised an exception, we swallow it silently with a log warning; the DB is consistent.

### 4. Two separate database URLs are required
The async FastAPI application uses `postgresql+asyncpg://` (`DATABASE_URL`). Alembic cannot use asyncpg because Alembic is synchronous. Alembic reads `DATABASE_SYNC_URL` using `psycopg2`. Both must be set. If only one is set, either the app or migrations will fail to start.

### 5. `NullPool` for Alembic
Alembic's `env.py` uses `NullPool`. The migration container is a one-shot process: it runs `alembic upgrade head` and exits. If a connection pool is open, the container process will hang waiting for pooled connections to be returned. `NullPool` creates connections on demand and discards them immediately, allowing clean exit.

### 6. `CLASS_NAMES` order is immutable after first deployment
The index of each class in `CLASS_NAMES` IS the `label_id` stored in the database. Predictions stored in the DB reference `label_id=11` to mean "invoice". If the list order ever changes after data has been written, every historical prediction's `label_id` becomes wrong. The list must never be reordered, extended in the middle, or shortened.

### 7. `casbin_rule` table name is singular
The `CasbinRule` ORM model uses `__tablename__ = "casbin_rule"` (singular), not `casbin_rules`. The casbin-sqlalchemy-adapter library expects exactly this name. The migration creates this table with the exact column names the adapter requires (`ptype`, `v0`–`v5`).

### 8. `security.py` ownership ambiguity
`app/core/security.py` was written by Mohamad because Ali's stub was empty and `user_service.register_user()` needed `hash_password()`. The spec lists this file as Ali's responsibility. Ali must take ownership and ensure the function names `hash_password(plain: str) -> str` and `verify_password(plain: str, hashed: str) -> bool` remain unchanged, since `user_service.py` imports them by name.

### 9. `relabeled_by` is a raw email string, not a FK
`Prediction.relabeled_by` stores the reviewer's email as a plain string, not a foreign key to the users table. This is intentional — it allows storing who relabeled a prediction even if that user account is later deleted, maintaining the audit trail integrity.

### 10. `audit_service.log_event` does NOT commit
`audit_service.log_event()` calls `audit_repository.create()` which calls `session.flush()`. It does not call `session.commit()`. This is required for atomicity: the mutation and its audit log entry must be committed together in one transaction by the parent service. If `log_event` committed independently, a failure between the mutation and the audit log would leave the DB in a split state.

---

## Project-Wide Flags (for team review)

### FLAG 1 — Jad must add `all_probs` to his output type
**File**: `app/classifier/inference/types.py`
**Required change**: Add `all_probs: dict[str, float]` to `PredictionResult`
**Why**: `prediction_service.create_prediction()` requires this field. Without it, Jad's inference worker cannot call the service.

### FLAG 2 — Aya must add `asyncpg` to dependencies
**File**: `pyproject.toml`
**Required change**: Add `asyncpg` to the dependencies list
**Why**: `app/db/session.py` uses `postgresql+asyncpg://`. Without `asyncpg` installed, `from app.db.session import get_session` raises `ModuleNotFoundError` at startup.

### FLAG 3 — Aya must set both DB URL env vars
**File**: `docker-compose.yml` (or `.env`)
**Required change**: Set `DATABASE_URL` (asyncpg URL) and `DATABASE_SYNC_URL` (psycopg2 URL) for both the app container and the alembic migrate container
**Why**: `session.py` reads `DATABASE_URL` (KeyError if missing). `alembic/env.py` reads `DATABASE_SYNC_URL` (KeyError if missing).

### FLAG 4 — Ali must match cache namespace strings
**File**: Ali's router files (wherever he adds `@cache()` decorators)
**Required change**: Use `namespace=f"batch:{batch_id}"`, `namespace=f"user:{user_id}"`, and `namespace="predictions:recent"` in his cache decorators
**Why**: `cache_service.py` calls `FastAPICache.clear(namespace=...)` with these exact strings. If Ali uses different strings, his cached responses will never be invalidated.

### FLAG 5 — Ali must import exceptions from `app.exceptions`
**File**: Ali's router files
**Required change**: `from app.exceptions import UserNotFound, BatchNotFound, LastAdminError, UnauthorizedRelabel` and map them to HTTP codes
**Why**: The services raise these exceptions. Without router-level handlers, FastAPI will return unhandled 500 errors.

### FLAG 6 — Ali must take ownership of `app/core/security.py`
**File**: `app/core/security.py`
**Status**: Mohamad wrote it (Ali's stub was empty). Function names are `hash_password()` and `verify_password()`.
**Required**: Ali must review it, confirm it meets his auth requirements, and not rename the functions (user_service imports them).

---

## Next Steps

For Mohamad specifically — nothing. All 23 tasks are done and tested.

For the team to integrate:

1. **Aya**: Add `asyncpg` to deps, set both `DATABASE_URL` and `DATABASE_SYNC_URL` in compose, run `alembic upgrade head` to create all tables
2. **Jad**: Add `all_probs: dict[str, float]` to `PredictionResult` in `app/classifier/inference/types.py`
3. **Ali**: Add exception handlers in routers, match cache namespace strings, take ownership of `security.py`
4. **Integration test**: Once Docker is up (Aya's step), run `pytest` in full mode to verify end-to-end (DB writes, Redis cache, actual HTTP responses)

---

## Full File Reference

### `app/db/base.py`
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### `app/core/constants.py`
```python
from enum import Enum

CONFIDENCE_THRESHOLD = 0.7

CLASS_NAMES: list[str] = [
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

class UserRole(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"
```

### `app/exceptions.py`
```python
class UserNotFound(Exception): pass
class BatchNotFound(Exception): pass
class DocumentNotFound(Exception): pass
class PredictionNotFound(Exception): pass
class LastAdminError(Exception): pass
class UnauthorizedRelabel(Exception): pass
```

### `app/services/batch_service.py` — key functions
```python
async def create_batch(session, request_id) -> BatchDomain:
    batch = await batch_repository.create(session, request_id)
    await session.commit()
    return BatchDomain.model_validate(batch)

async def add_document(session, batch_id, filename, blob_bucket, blob_path) -> DocumentDomain:
    doc = await document_repository.create(session, batch_id, filename, blob_bucket, blob_path)
    await session.commit()
    return DocumentDomain.model_validate(doc)

async def update_status(session, batch_id, status) -> BatchDomain:
    batch = await batch_repository.update_status(session, batch_id, status)
    if batch is None:
        raise BatchNotFound
    await audit_service.log_event(session, "system", "status_change", f"batch:{batch_id}")
    await session.commit()
    await cache_service.invalidate_batch(batch_id)
    return BatchDomain.model_validate(batch)
```

### `app/services/prediction_service.py` — key function
```python
async def relabel(session, prediction_id, new_label, reviewer) -> PredictionDomain:
    prediction = await prediction_repository.get_by_id(session, prediction_id)
    if prediction is None:
        raise PredictionNotFound
    if prediction.confidence >= CONFIDENCE_THRESHOLD:   # 0.7 — guard is >=
        raise UnauthorizedRelabel
    new_label_id = CLASS_NAMES.index(new_label)
    updated = await prediction_repository.update_label(
        session, prediction_id, new_label_id, new_label, reviewer
    )
    await audit_service.log_event(session, reviewer, "relabel", f"prediction:{prediction_id}")
    await session.commit()
    await cache_service.invalidate_predictions()
    return PredictionDomain.model_validate(updated)
```

### `app/services/user_service.py` — key function
```python
async def toggle_role(session, user_id, new_role, actor) -> UserDomain:
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise UserNotFound
    if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
        admin_count = await user_repository.count_by_role(session, UserRole.ADMIN)
        if admin_count <= 1:
            raise LastAdminError
    updated = await user_repository.update_role(session, user_id, new_role)
    await audit_service.log_event(session, actor, "role_change", f"user:{user_id}")
    await session.commit()
    await cache_service.invalidate_user(user_id)
    return UserDomain.model_validate(updated)
```

### `app/services/cache_service.py` — namespace constants
```python
BATCH_NAMESPACE = "batch"
USER_NAMESPACE = "user"
PREDICTIONS_RECENT_NAMESPACE = "predictions:recent"

# Ali must use these exact namespace strings in his @cache() decorators:
# @cache(namespace=f"batch:{batch_id}")    → cleared by invalidate_batch(batch_id)
# @cache(namespace=f"user:{user_id}")      → cleared by invalidate_user(user_id)
# @cache(namespace="predictions:recent")  → cleared by invalidate_predictions()
```

---

## Architecture Rules (verified)

| Rule | Status | Evidence |
|------|--------|----------|
| ORM models only imported by repositories | Verified | grep shows no service or router imports from `app.db.models` |
| Repositories raise no HTTP exceptions | Verified | No `HTTPException` import in any repository file |
| Repositories do not invalidate caches | Verified | No `cache_service` import in any repository file |
| Services own all transaction boundaries | Verified | Every `commit()` call is in a service function |
| Cache invalidation only in service layer | Verified | `FastAPICache.clear()` only called from `cache_service.py` |
| Domain models are distinct from ORM models | Verified | Separate Pydantic classes in `app/domain/`, ORM in `app/db/models.py` |
| No hardcoded secrets | Verified | Passwords hashed via passlib, DB URL from env var |
| Audit log is append-only | Verified | `audit_repository.py` has no update or delete functions |
