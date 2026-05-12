# Task 4 — app/db/models.py

## What it does

Defines all six SQLAlchemy ORM classes that map to database tables. This is the schema of the entire system expressed in Python. Every read and every write in the project flows through these classes — but only through the repository layer. No router, no service, and no worker imports from this file directly. Only repositories do.

---

## The 6 tables

### User
Inherits from `SQLAlchemyBaseUserTable[int]` (fastapi-users) and `Base` (ours).

`SQLAlchemyBaseUserTable` already provides:
- `email` (String, unique, indexed)
- `hashed_password` (String)
- `is_active` (Boolean, default True)
- `is_superuser` (Boolean, default False)
- `is_verified` (Boolean, default False)

We add:
- `id` (Integer, primary key, autoincrement) — explicit integer PK overrides fastapi-users UUID default
- `role` (String(50), default=`UserRole.AUDITOR`) — the three-role permission system

**Why inherit from `SQLAlchemyBaseUserTable`?**
Ali's `app/auth/users.py` configures fastapi-users to use this exact model. fastapi-users needs the email/hashed_password/is_active/is_superuser/is_verified fields to exist on the model — inheriting from `SQLAlchemyBaseUserTable` guarantees that without us manually defining every field. If we wrote a plain User without this base, Ali's auth setup would break.

**Why integer PK and not UUID?**
The contract payloads in tasks.pdf use integer IDs (`batch_id: 12`, `document_id: 44`). Keeping all PKs as integers is consistent and simpler.

---

### Batch
- `id` — integer primary key
- `request_id` — UUID string from Aya's ingest worker, carried end-to-end for log tracing
- `status` — string (values from `BatchStatus` enum: pending/processing/done/failed)
- `created_at` — set by the DB server on insert via `func.now()`

---

### Document
- `id` — integer primary key, **this id goes into the Redis job payload** (`document_id: 44`)
- `batch_id` — foreign key to `batches.id`
- `filename` — original filename from SFTP drop (e.g. `file1.tiff`)
- `blob_bucket` — MinIO bucket name (e.g. `documents`)
- `blob_path` — full path inside the bucket (e.g. `raw/batch_12/file1.tiff`)
- `created_at` — set by DB server

**Why does this table exist?**
tasks.pdf lists 5 tables but shows `batch_service.add_document()` returning a document with an id, and the Redis job contains `document_id: 44`. That document_id must reference a real row. A batch can logically contain multiple documents (SFTP can drop multiple files). The documents table records each file individually so that each prediction is traceable to a specific file.

---

### Prediction
The most field-heavy model. Every field maps directly to Jad's contract payload:

- `job_id` — the RQ job UUID, for tracing this prediction back to a specific worker run
- `batch_id` — FK to batches
- `document_id` — FK to documents
- `label_id` — integer index into CLASS_NAMES (0–15)
- `label` — string class name (e.g. `"invoice"`)
- `confidence` — float top-1 probability (e.g. `0.93`)
- `top5` — JSON list of top-5 predictions, each with label_id/label/confidence
- `all_probs` — JSON dict of all 16 class probabilities
- `model_sha256` — SHA-256 of the weights file that produced this prediction
- `overlay_bucket` — MinIO bucket of the annotated overlay PNG
- `overlay_path` — path to the overlay PNG inside the bucket
- `relabeled_by` — nullable; stores the reviewer's email if a relabel happened
- `request_id` — carried from Aya's ingest job for end-to-end log tracing
- `created_at` — set by DB server

**Why `top5` and `all_probs` as JSON?**
These are variable-length structured data. Storing them as JSON in Postgres means no separate join table is needed and the full probability distribution is always available next to the prediction row. The trade-off is no SQL-level filtering on individual probabilities — but the project never queries inside these fields, only reads them whole.

**Note on `all_probs` vs Jad's types.py:**
Jad's `PredictionResult` in `app/classifier/inference/types.py` does not include `all_probs`. However, the contract in tasks.pdf (Jad → Mohamad, page 6) explicitly includes it. Jad needs to add `all_probs` to his `PredictionResult` type and pass it to `create_prediction()`. This is flagged for Jad.

---

### AuditLog
- `actor` — email of the user who performed the action
- `action` — string describing what happened (e.g. `"role_change"`, `"relabel"`, `"batch_status_change"`, `"prediction_created"`)
- `target` — string identifying what was changed (e.g. `"user_7"`, `"prediction_55"`, `"batch_12"`)
- `timestamp` — set by DB server

project-6.pdf requires audit entries for: every role change, every relabel, every batch state change. These three cases are covered by `user_service`, `prediction_service`, and `batch_service` respectively.

---

### CasbinRule
Required by `casbin-sqlalchemy-adapter`. The adapter reads and writes this table to enforce RBAC policies.

Structure:
- `ptype` — policy type: `"p"` for permission rules, `"g"` for role-assignment rules
- `v0` through `v5` — policy fields (all nullable strings)

Example rows Ali's `seed_policies.py` will insert:
```
ptype=p, v0=admin,    v1=/admin/users/{id}/role, v2=PATCH
ptype=p, v0=reviewer, v1=/predictions/{id},      v2=PATCH
ptype=p, v0=auditor,  v1=/batches,               v2=GET
ptype=g, v0=user@example.com, v1=admin
```

v3–v5 are nullable and unused for basic RBAC but required by the adapter schema. The table name `casbin_rule` (not `casbin_rules`) is what the adapter expects by default.

---

## Approach and defense

**No ORM relationships defined.**
No `relationship("Document", back_populates=...)` on Batch, no `relationship("Prediction", ...)` on Document. Repositories do explicit queries with joins or separate lookups. ORM relationships encourage lazy loading, which causes N+1 query bugs and sessions that outlive their scope. The project spec says repositories own SQL — relationships blur that boundary.

**SQLAlchemy 2.x `mapped_column` style throughout.**
The old `Column(Integer, ...)` style works in 2.x but is legacy. `mapped_column` with `Mapped[type]` annotations gives full type checking and is the correct style for this codebase.

**`server_default=func.now()` for timestamps.**
This sets the timestamp at the database level, not in Python. It is consistent regardless of which process inserts the row (API, worker, ingest worker) and does not depend on system clock synchronization between containers.

**`Mapped[Any]` for JSON columns.**
SQLAlchemy's `JSON` type stores and retrieves Python dicts/lists. Using `Mapped[Any]` is accurate — the DB type is JSON but Python sees whatever was stored. A stricter type like `Mapped[list[dict]]` would be incorrect because SQLAlchemy doesn't enforce inner structure.

---

## Who depends on this

| Who | File | What they need |
|---|---|---|
| Mohamad (Task 6) | alembic/env.py | imports `Base` — models must be imported before env.py runs so Alembic sees all tables |
| Mohamad (Tasks 13–17) | repositories/ | ALL repositories import their model from here |
| Ali | app/auth/users.py | imports `User` to configure fastapi-users |
| Ali | app/auth/casbin.py | imports `CasbinRule` to configure the adapter |

## Critical note for Alembic (Task 6)

`alembic/env.py` must import all models from `app.db.models` before `Base.metadata` is passed to Alembic. If models are not imported, Alembic's autogenerate sees an empty metadata and generates an empty migration. The standard pattern is:

```python
from app.db import models  # noqa: F401 — ensures all models are registered
from app.db.base import Base
target_metadata = Base.metadata
```

## Critical note for Jad

`all_probs` is a field in the `Prediction` table and is required by the contract in tasks.pdf (page 6). Jad's `PredictionResult` in `types.py` currently does not include `all_probs`. Jad must add it before calling `prediction_service.create_prediction()`.

## Critical note for Ali

`CasbinRule` table name is `casbin_rule` (singular). The `casbin-sqlalchemy-adapter` expects this exact name. When configuring the adapter in `app/auth/casbin.py`, use this model directly or configure the adapter to point at this table.

The `UserRole` enum values (`admin`, `reviewer`, `auditor`) in `constants.py` must be used as-is in Casbin policy strings in `seed_policies.py`.
