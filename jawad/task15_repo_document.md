# Task 15 — app/repositories/document_repository.py

## What it does

SQL-only functions for the `documents` table. **This file was created new** — the repo skeleton had no `document_repository.py`. It completes the data layer for `batch_service.add_document()`, which Aya depends on to get `document.id` for the Redis job payload.

---

## Functions

| Function | Returns |
|---|---|
| `create(session, batch_id, filename, blob_bucket, blob_path)` | `Document` — new row with populated `id` |
| `get_by_id(session, document_id)` | `Document \| None` |
| `list_by_batch_id(session, batch_id)` | `list[Document]` ordered by `created_at` |

---

## Critical: `id` must be populated on return

Aya's SFTP worker does:
```python
document = await batch_service.add_document(...)
redis_job = {"document_id": document.id, ...}
```

The `flush()` + `refresh()` pattern guarantees `document.id` is set before `create()` returns. Without `refresh()`, the `created_at` timestamp would also be missing (it's a `server_default`).

---

## `list_by_batch_id` ordering

`ORDER BY created_at ASC` — documents listed in upload order. This is the natural order for processing and display.

---

## No `update` function

Documents are immutable once created. The blob coordinates (`blob_bucket`, `blob_path`) point to the original file in MinIO and never change. If a file needs to be replaced, a new document row is created.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `Document` | `app.db.models` | ✓ Task 4 |
| `AsyncSession` | `sqlalchemy.ext.asyncio` | ✓ |

## Who calls this

Only `app/services/batch_service.py` (via `add_document`).
