# Task 12 — app/domain/audit.py

## What it does

Defines `AuditLogDomain`, a Pydantic model representing a single audit log entry as returned by the service layer. Audit logs are append-only — they are created but never updated or deleted. This domain model is the read-side representation.

---

## Field-by-field rationale

| Field | Type | Why |
|---|---|---|
| `actor` | `str` | Email of the user who performed the action. Stored as email string (not user_id) so the log remains readable even if the user is deleted. |
| `action` | `str` | Verb describing what happened. Expected values: `"relabel"`, `"status_change"`, `"upload"`. Kept as plain string — no enum — so new action types can be added without a schema change. |
| `target` | `str` | Affected resource as a `"type:id"` string, e.g. `"prediction:42"`, `"batch:7"`. Allows filtering logs by resource without a JOIN. |
| `timestamp` | `datetime` | Timezone-aware datetime from Postgres `DateTime(timezone=True)`. Used for chronological ordering and audit trail exports. |

---

## Append-only design

`AuditLogDomain` has no mutable fields and no update path. The `audit_service` only ever calls `create()` — there is no `update()` or `delete()` in the audit repository. This is intentional: audit logs are an immutable record of what happened.

---

## `target` format convention

The `target` field follows the pattern `"<resource_type>:<id>"`:
- `"prediction:42"` — a prediction was relabeled
- `"batch:7"` — a batch status changed

This convention must be consistent across all callers of `audit_service.log()` so that filtering by target type works with a simple `LIKE 'prediction:%'` query.

---

## Who uses this

| Who | Where | What they need |
|---|---|---|
| Ali | `app/api/routers/audit.py` | Return type for `GET /audit` (admin-only log viewer) |
| Mohamad | `app/services/audit_service.py` | Return type from `log()`, `list_logs()` |
| Mohamad | `app/repositories/audit_repo.py` | Output of `create()`, `list_all()`, `list_by_actor()` |
| Mohamad | `batch_service.update_status()` | Calls `audit_service.log()` internally on every status transition |
| Mohamad | `prediction_service.relabel()` | Calls `audit_service.log()` after a successful relabel |

---

## What it does NOT include

- No `batch_id` or `document_id` FK — those are embedded in the `target` string, not as typed foreign keys. Keeps the audit table schema simple.
- No `metadata` / `detail` JSON field — action + target is enough granularity for this project. If more detail is needed, extend `target` to be a longer string.
