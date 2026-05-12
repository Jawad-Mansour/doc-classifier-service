# Mohamad — Complete Work Overview
> Branch: feature/mohamad-backend-db
> Role: Backend + DB + Services (System Spine)
> All 23 tasks complete. 13/13 tests passing.

---

## What was built

Mohamad owns the entire data layer of the document classifier service. Every other teammate (Aya, Jad, Ali) depends on this layer to function. Nothing runs without it.

The layer has 5 levels, built in strict order:

```
Foundation      → DB base, ORM models, session, migrations
Shared values   → constants, exceptions
Contracts       → domain models (what services return to routers)
SQL layer       → repositories (pure SQL, no logic)
Business layer  → services (logic, transactions, audit, cache)
Tests           → unit tests for all business rules
```

---

## File-by-file breakdown

### Task 1 — `app/db/base.py`
Single class. The SQLAlchemy declarative base that every ORM model inherits from. Alembic also reads its `.metadata` to know what tables exist.

```python
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
```

Every ORM model in the project inherits from this. Without it, nothing can be persisted.

---

### Task 2 — `app/core/constants.py`
Shared values used across the entire codebase. One source of truth.

- `CLASS_NAMES` — list of 16 RVL-CDIP document classes in exact order. The index in this list IS the `label_id`. Order must never change after first deployment.
- `CONFIDENCE_THRESHOLD = 0.7` — predictions with confidence >= 0.7 cannot be relabeled by a human reviewer.
- `BatchStatus` enum — `pending / processing / done / failed`
- `UserRole` enum — `admin / reviewer / auditor`

Verified against Jad's `model_card.json` for class order correctness.

---

### Task 3 — `app/exceptions.py`
Six plain exception classes. Services raise them. Ali's routers catch them and return the correct HTTP status code.

```python
class UserNotFound(Exception): pass
class BatchNotFound(Exception): pass
class DocumentNotFound(Exception): pass
class PredictionNotFound(Exception): pass
class LastAdminError(Exception): pass       # → 400
class UnauthorizedRelabel(Exception): pass  # → 403
```

No logic inside them — they are pure signal classes.

---

### Task 4 — `app/db/models.py`
Six SQLAlchemy 2.x ORM models using the modern `mapped_column` / `Mapped` style.

| Model | Table | Key decisions |
|---|---|---|
| `User` | `users` | Inherits `SQLAlchemyBaseUserTable[int]` for fastapi-users compatibility + adds `role` column |
| `Batch` | `batches` | `status` string, `created_at` with `server_default=func.now()` |
| `Document` | `documents` | FK to `batches.id`, `blob_bucket` + `blob_path` for MinIO coordinates |
| `Prediction` | `predictions` | FK to both `batches.id` and `documents.id`, `top5` and `all_probs` as JSON columns, `relabeled_by` nullable |
| `AuditLog` | `audit_logs` | `actor`, `action`, `target`, `timestamp` — append-only |
| `CasbinRule` | `casbin_rule` | Exact schema required by casbin-sqlalchemy-adapter |

Rule: only repositories import from this file.

---

### Task 5 — `app/db/session.py`
Creates the async SQLAlchemy engine and session factory. Every repository receives a session from here via FastAPI dependency injection.

```python
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

Key decision: `expire_on_commit=False` — after a service calls `session.commit()`, ORM objects remain readable in Python without triggering a second DB query. Without this, accessing `batch.id` after commit raises `DetachedInstanceError`.

Uses `DATABASE_URL` with `postgresql+asyncpg://` driver (async). Requires `asyncpg` to be in dependencies.

---

### Task 6 — `alembic.ini` + `alembic/env.py` + `alembic/script.py.mako`

**alembic.ini** — configuration file:
- `script_location = alembic` — migrations live in `alembic/`
- `prepend_sys_path = .` — adds project root to sys.path so `from app.db.base import Base` works
- No hardcoded database URL

**alembic/env.py** — the migration runner:
- Imports `from app.db import models  # noqa: F401` — critical: registers all ORM models with `Base.metadata` before autogenerate runs. Without this import, Alembic sees an empty schema.
- Reads `DATABASE_SYNC_URL` env var (psycopg2 sync driver — Alembic cannot use asyncpg)
- `NullPool` — the migrate container is one-shot, connection pooling would prevent it from exiting cleanly

**alembic/script.py.mako** — template for generated migration files (was empty, filled with standard template).

Two separate DB URL env vars are required:
- `DATABASE_URL` → `postgresql+asyncpg://` (for the app)
- `DATABASE_SYNC_URL` → `postgresql+psycopg2://` (for Alembic)

---

### Task 7 — `alembic/versions/0001_initial.py`
The first (and only) Alembic migration. Written manually because no live DB is available without Docker.

`upgrade()` creates all 6 tables in dependency order (FK targets before FK sources):
1. `users` — no FK dependencies
2. `batches` — no FK dependencies
3. `documents` → FK to `batches.id`
4. `predictions` → FK to `batches.id` and `documents.id`
5. `audit_logs` — no FK dependencies
6. `casbin_rule` — no FK dependencies

`downgrade()` drops in reverse order.

Every column, nullable flag, server_default, and FK was verified against the ORM models in Task 4.

---

### Task 8 — `app/domain/user.py`
Pydantic model representing a user as returned by services.

```python
class UserDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    role: str
```

`from_attributes=True` allows `UserDomain.model_validate(orm_user_row)`. `hashed_password` is intentionally excluded — it must never leave the service layer.

---

### Task 9 — `app/domain/batch.py`
```python
class BatchDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    request_id: str
    status: str
    created_at: datetime
```

---

### Task 10 — `app/domain/document.py`
This file was missing from the repo skeleton entirely — created new.

```python
class DocumentDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: int
    filename: str
    blob_bucket: str
    blob_path: str
    created_at: datetime
```

Aya reads `document.id` from this model to build the Redis job payload. The `id` being populated is the critical guarantee.

---

### Task 11 — `app/domain/prediction.py`
The largest domain model. Carries Jad's full inference output.

```python
class PredictionDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: str
    batch_id: int
    document_id: int
    label_id: int        # index into CLASS_NAMES
    label: str           # CLASS_NAMES[label_id]
    confidence: float    # softmax score, compared against CONFIDENCE_THRESHOLD
    top5: list[Any]      # Jad's top-5 predictions
    all_probs: dict[str, Any]  # full softmax distribution
    model_sha256: str    # 64-char hex, audit trail for which model weights ran
    overlay_bucket: str  # MinIO bucket for GradCAM overlay
    overlay_path: str    # MinIO object key for GradCAM overlay
    relabeled_by: str | None  # None = model result, non-null = reviewer email
    request_id: str
    created_at: datetime
```

**FLAG FOR JAD**: `all_probs` is required here and in `prediction_repository.create()` but was missing from his `PredictionResult` in `app/classifier/inference/types.py`. He must add it.

---

### Task 12 — `app/domain/audit.py`
```python
class AuditLogDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor: str     # email of who acted, or "system" for automated events
    action: str    # "relabel" | "status_change" | "role_change" | "prediction_created"
    target: str    # "type:id" format e.g. "prediction:42"
    timestamp: datetime
```

---

### Task 13 — `app/repositories/user_repository.py`
Five async functions. SQL only. No business logic.

| Function | What it does |
|---|---|
| `get_by_id(session, user_id)` | `session.get(User, user_id)` |
| `get_by_email(session, email)` | `SELECT WHERE email = ?` |
| `count_by_role(session, role)` | `SELECT COUNT(*) WHERE role = ?` — needed for LastAdminError guard |
| `create(session, email, hashed_password, role)` | `INSERT`, flush, refresh |
| `update_role(session, user_id, new_role)` | mutate + flush + refresh |

All write functions use `flush()` + `refresh()` pattern: flush sends SQL within the open transaction, refresh reads back server-generated values (`id`, `created_at`). Services call `commit()`.

---

### Task 14 — `app/repositories/batch_repository.py`
Four async functions.

| Function | What it does |
|---|---|
| `create(session, request_id)` | INSERT with `status="pending"`, flush, refresh |
| `get_by_id(session, batch_id)` | `session.get(Batch, batch_id)` |
| `list_all(session)` | SELECT all, ORDER BY created_at DESC |
| `update_status(session, batch_id, status)` | mutate + flush + refresh, returns None if not found |

---

### Task 15 — `app/repositories/document_repository.py`
Three async functions. **File was missing from the skeleton — created new.**

| Function | What it does |
|---|---|
| `create(session, batch_id, filename, blob_bucket, blob_path)` | INSERT, flush, refresh — returns Document with `id` set |
| `get_by_id(session, document_id)` | `session.get(Document, document_id)` |
| `list_by_batch_id(session, batch_id)` | SELECT WHERE batch_id, ORDER BY created_at ASC |

The `id` being set on return from `create()` is critical for Aya's Redis job payload.

---

### Task 16 — `app/repositories/prediction_repository.py`
Five async functions.

| Function | What it does |
|---|---|
| `create(session, ...13 fields...)` | INSERT all prediction fields, flush, refresh |
| `get_by_id(session, prediction_id)` | `session.get(Prediction, prediction_id)` |
| `list_by_batch_id(session, batch_id)` | SELECT WHERE batch_id, ASC order |
| `get_recent(session, limit)` | SELECT all, DESC order, LIMIT |
| `update_label(session, prediction_id, new_label_id, new_label, relabeled_by)` | Updates both `label_id` AND `label` together — they must never diverge |

---

### Task 17 — `app/repositories/audit_repository.py`
Three async functions. Append-only by design — no update or delete.

| Function | What it does |
|---|---|
| `create(session, actor, action, target)` | INSERT, flush, refresh |
| `list_all(session)` | SELECT all, ORDER BY timestamp DESC |
| `list_by_actor(session, actor)` | SELECT WHERE actor, DESC order |

---

### Task 18 — `app/services/audit_service.py`
Support service. Never called directly by routers — called by other services after writes.

```python
async def log_event(session, actor, action, target) -> None
async def list_logs(session) -> list[AuditLogDomain]
async def list_logs_by_actor(session, actor) -> list[AuditLogDomain]
```

`log_event` does NOT commit. It is always called within another service's transaction. The parent service commits once at the end, making the mutation and its audit log atomic.

`actor = "system"` for automated events (inference worker). Human actor events pass the user's email.

---

### Task 19 — `app/services/cache_service.py`
Support service. Wraps fastapi-cache2's `FastAPICache.clear()`. Silent on failure — cache invalidation failure is not fatal, the DB write already committed.

```python
async def invalidate_batch(batch_id: int) -> None       # clears "batch:{id}"
async def invalidate_user(user_id: int) -> None         # clears "user:{id}"
async def invalidate_predictions() -> None              # clears "predictions:recent"
```

**Contract for Ali**: he must use these exact namespace strings in his `@cache()` decorators:
- `@cache(namespace=f"batch:{batch_id}")`
- `@cache(namespace=f"user:{user_id}")`
- `@cache(namespace="predictions:recent")`

Cache invalidation always happens AFTER `session.commit()`. Order matters: if we invalidated before commit and commit failed, the next request would re-cache stale data.

---

### Task 20 — `app/services/batch_service.py`
Primary service for Aya. She calls `create_batch` and `add_document` before pushing every Redis job. Jad calls `update_status` after inference completes.

| Function | Logic | Commits? |
|---|---|---|
| `create_batch(session, request_id)` | create batch, return BatchDomain | Yes |
| `add_document(session, batch_id, ...)` | create document, return DocumentDomain with `id` | Yes |
| `get_batch(session, batch_id)` | fetch, raise BatchNotFound if missing | No |
| `list_batches(session)` | fetch all | No |
| `update_status(session, batch_id, status)` | update + audit log → commit → invalidate cache | Yes |

`update_status` operation order:
```
batch_repo.update_status()      → flush
audit_service.log_event()       → flush (same transaction)
session.commit()                → atomic commit of both
cache_service.invalidate_batch()→ after commit
return BatchDomain
```

---

### Task 21 — `app/services/prediction_service.py`
Critical service for Jad. `create_prediction` is the function his inference worker calls.

| Function | Logic | Commits? |
|---|---|---|
| `create_prediction(session, ...13 params...)` | save + audit log → commit → invalidate cache | Yes |
| `list_predictions(session, batch_id)` | fetch by batch | No |
| `get_recent(session, limit=20)` | fetch most recent N | No |
| `relabel(session, prediction_id, new_label, reviewer)` | GUARD + update + audit → commit → invalidate | Yes |

**Relabel guard** (from project spec):
```python
if prediction.confidence >= CONFIDENCE_THRESHOLD:  # 0.7
    raise UnauthorizedRelabel
```
High-confidence predictions (>= 0.7) cannot be overridden by humans. Only uncertain predictions (< 0.7) can be relabeled.

`new_label_id = CLASS_NAMES.index(new_label)` — derives the integer label_id from the string label to keep both columns in sync.

---

### Task 22 — `app/services/user_service.py`
Manages user registration and role management.

| Function | Logic | Commits? |
|---|---|---|
| `register_user(session, email, password)` | hash password → create user (role=auditor) → commit | Yes |
| `toggle_role(session, user_id, new_role, actor)` | GUARD + update + audit → commit → invalidate cache | Yes |

**Last-admin guard** (from project spec — "What happens when the only admin tries to demote themselves?"):
```python
if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
    admin_count = await user_repository.count_by_role(session, UserRole.ADMIN)
    if admin_count <= 1:
        raise LastAdminError
```
Guard only fires when demoting an admin to a non-admin role. Promoting to admin is always allowed.

Password hashing uses `app/core/security.py` (passlib bcrypt). **Note: the spec lists `security.py` as Ali's file. Mohamad wrote it because Ali's stub was empty and user_service needed it. Ali must take ownership — function names `hash_password()` and `verify_password()` must stay the same.**

---

### Task 23 — `tests/services/`
Unit tests for all business rules. No real DB or Redis needed — everything is mocked with `AsyncMock`.

**13 tests across 3 files:**

`test_user_service.py` (4 tests):
1. `toggle_role` raises `LastAdminError` when demoting the last admin — verifies `update_role` is never called
2. `toggle_role` raises `UserNotFound` when user doesn't exist
3. `toggle_role` succeeds when 2+ admins exist
4. `toggle_role` calls `audit_service.log_event` with correct args and `cache_service.invalidate_user`

`test_prediction_service.py` (6 tests):
5. `relabel` raises `UnauthorizedRelabel` when `confidence == 0.7` (boundary — guard is `>=`)
6. `relabel` raises `UnauthorizedRelabel` when `confidence > 0.7`
7. `relabel` succeeds when `confidence < 0.7` — verifies label + relabeled_by updated
8. `relabel` raises `PredictionNotFound` when prediction doesn't exist
9. `relabel` calls `audit_service.log_event` with reviewer email + "relabel"
10. `create_prediction` calls `audit_service.log_event` with "system" + "prediction_created"

`test_batch_service.py` (3 tests):
11. `update_status` raises `BatchNotFound` when batch doesn't exist
12. `update_status` calls `audit_service.log_event` with "system" + "status_change" + correct target
13. `add_document` returns `DocumentDomain` with a populated `id` — critical for Aya's Redis job

Mocking strategy: `types.SimpleNamespace` for fake ORM rows (works with `from_attributes=True`), `patch()` targeting module-level references, `AsyncMock()` for session.

`asyncio_mode = "auto"` added to `pyproject.toml` so all `async def test_*` functions run automatically without needing `@pytest.mark.asyncio` decorators.

---

## Architecture rules verified

| Rule (from spec) | Status |
|---|---|
| ORM models only imported by repositories | ✓ verified by import scan |
| Repositories do not raise HTTP exceptions | ✓ verified by grep |
| Repositories do not invalidate caches | ✓ verified by grep |
| Services own transaction boundaries | ✓ all writes commit in service |
| Cache invalidation only in service layer | ✓ only cache_service calls FastAPICache |
| Domain models distinct from ORM models | ✓ separate Pydantic models in app/domain/ |
| No hardcoded secrets | ✓ no plaintext passwords in code |

---

## Contracts verified against spec

### Mohamad → Aya
```python
batch = batch_service.create_batch(request_id="uuid-abc-123")   # ✓
document = batch_service.add_document(
    batch_id=batch.id,
    filename="file1.tiff",
    blob_bucket="documents",
    blob_path="raw/batch_12/file1.tiff",
)
# batch.id and document.id both populated ✓
```

### Mohamad → Jad
```python
prediction_service.create_prediction(
    job_id="uuid",
    batch_id=12,
    document_id=44,
    label_id=11,
    label="invoice",
    confidence=0.93,
    top5=[...],
    all_probs={"invoice": 0.93, ...},
    model_sha256="dc3737...",
    overlay_bucket="documents",
    overlay_path="overlays/batch_12/file1_overlay.png",
    request_id="uuid-abc-123",
)  # ✓ all params present
```

### Mohamad → Ali
```python
prediction_service.list_predictions(batch_id)  # ✓
batch_service.list_batches()                   # ✓
batch_service.get_batch(batch_id)              # ✓
audit_service.list_logs()                      # ✓
```

---

## Files owned

| File | Task |
|---|---|
| `app/db/base.py` | 1 |
| `app/core/constants.py` | 2 |
| `app/exceptions.py` | 3 |
| `app/db/models.py` | 4 |
| `app/db/session.py` | 5 |
| `alembic.ini` + `alembic/env.py` + `alembic/script.py.mako` | 6 |
| `alembic/versions/0001_initial.py` | 7 |
| `app/domain/user.py` | 8 |
| `app/domain/batch.py` | 9 |
| `app/domain/document.py` | 10 |
| `app/domain/prediction.py` | 11 |
| `app/domain/audit.py` | 12 |
| `app/repositories/user_repository.py` | 13 |
| `app/repositories/batch_repository.py` | 14 |
| `app/repositories/document_repository.py` | 15 (new file) |
| `app/repositories/prediction_repository.py` | 16 |
| `app/repositories/audit_repository.py` | 17 |
| `app/services/audit_service.py` | 18 |
| `app/services/cache_service.py` | 19 |
| `app/services/batch_service.py` | 20 |
| `app/services/prediction_service.py` | 21 |
| `app/services/user_service.py` | 22 |
| `tests/services/test_*.py` (3 files) | 23 |
| `app/core/security.py` | written for Task 22 — Ali owns this per spec |

---

## What teammates still need to do

| Who | What |
|---|---|
| **Jad** | Add `all_probs: dict[str, float]` to `PredictionResult` in `app/classifier/inference/types.py` |
| **Ali** | Take ownership of `app/core/security.py` — keep `hash_password()` and `verify_password()` function names |
| **Ali** | Use namespace strings `"batch:{id}"`, `"user:{id}"`, `"predictions:recent"` in his `@cache()` decorators |
| **Aya** | Add `asyncpg` to dependencies — `psycopg2-binary` is sync-only, can't drive async SQLAlchemy |
| **Aya** | Set both `DATABASE_URL` (asyncpg) and `DATABASE_SYNC_URL` (psycopg2) in docker-compose |
