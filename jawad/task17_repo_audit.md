# Task 17 — app/repositories/audit_repository.py

## What it does

SQL-only functions for the `audit_logs` table. Append-only — no update or delete. The simplest repository in the project.

---

## Functions

| Function | Returns |
|---|---|
| `create(session, actor, action, target)` | `AuditLog` |
| `list_all(session)` | `list[AuditLog]` ordered by `timestamp` DESC |
| `list_by_actor(session, actor)` | `list[AuditLog]` filtered by actor, DESC |

---

## Append-only design

There is no `update()` or `delete()` function. Audit logs are immutable once written. This is intentional — the audit trail must be tamper-evident. If a log entry needs to be corrected, a new entry is added.

---

## `target` format

The `target` field follows the `"type:id"` convention enforced by `audit_service`:
- `"prediction:42"` — a relabel event
- `"batch:12"` — a status change
- `"user:7"` — a role change

The repo stores whatever string it receives. The convention is the service's responsibility.

---

## `create()` does not set `timestamp`

`AuditLog` has `timestamp` with `server_default=func.now()`. The repo lets the DB set it — no Python `datetime.now()`. This ensures all timestamps are in the DB server's timezone and are consistent with the `created_at` on other tables.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `AuditLog` | `app.db.models` | ✓ Task 4 |
| `AsyncSession` | `sqlalchemy.ext.asyncio` | ✓ |

## Who calls this

Only `app/services/audit_service.py`.
