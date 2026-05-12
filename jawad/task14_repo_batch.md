# Task 14 — app/repositories/batch_repository.py

## What it does

SQL-only functions for the `batches` table. No business logic, no audit calls, no cache calls.

---

## Functions

| Function | Returns |
|---|---|
| `create(session, request_id)` | `Batch` — new row with `status="pending"` |
| `get_by_id(session, batch_id)` | `Batch \| None` |
| `list_all(session)` | `list[Batch]` ordered newest-first |
| `update_status(session, batch_id, status)` | `Batch \| None` |

---

## `create()` — status default

`Batch(request_id=request_id, status="pending")` — status is hardcoded to `"pending"` at creation time. The repo doesn't import `BatchStatus` because it's just writing a string. Status transitions happen via `update_status()`, and the transition guard logic lives in the service.

---

## `list_all` ordering

`ORDER BY created_at DESC` — most recent batch first. This matches how Ali's `GET /batches` endpoint will want to present them.

---

## `update_status` returns None on miss

If `batch_id` doesn't exist, returns `None`. The service catches this and raises `BatchNotFound`. The repo itself does not raise exceptions.

---

## flush + refresh pattern

Same as all write repos: `flush()` sends SQL within the transaction, `refresh()` reads back server-generated values (`id`, `created_at`). Service calls `commit()` after completing the full business operation.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `Batch` | `app.db.models` | ✓ Task 4 |
| `AsyncSession` | `sqlalchemy.ext.asyncio` | ✓ |

## Who calls this

Only `app/services/batch_service.py`.
