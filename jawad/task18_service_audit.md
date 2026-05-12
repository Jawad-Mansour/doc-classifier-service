# Task 18 — app/services/audit_service.py

## What it does

Support service. Never called by routers directly — called internally by batch_service, prediction_service, and user_service after every write that requires a paper trail. Also exposes `list_logs()` which Ali calls from `GET /audit`.

---

## Functions

| Function | Commits? | Who calls |
|---|---|---|
| `log_event(session, actor, action, target)` | No | batch/prediction/user services |
| `list_logs(session)` | No | Ali's audit router |
| `list_logs_by_actor(session, actor)` | No | Ali's audit router (filtered view) |

---

## No commit in log_event — by design

`log_event` is always called from within another service's transaction. Example in `batch_service.update_status()`:

```
1. batch_repo.update_status()   → flush (same transaction)
2. audit_service.log_event()    → flush (same transaction)
3. session.commit()             → commits BOTH atomically
4. cache_service.invalidate_batch()
```

If `log_event` committed independently, a subsequent failure in the parent service would leave a dangling audit log with no matching DB change. By deferring the commit to the parent, both the mutation and its audit record are always committed together or not at all.

---

## target format contract

`log_event` accepts any `target` string. The expected format is `"type:id"`:

| Caller | action | target |
|---|---|---|
| batch_service.update_status | `"status_change"` | `"batch:{batch_id}"` |
| prediction_service.create_prediction | `"prediction_created"` | `"document:{document_id}"` |
| prediction_service.relabel | `"relabel"` | `"prediction:{prediction_id}"` |
| user_service.toggle_role | `"role_change"` | `"user:{user_id}"` |

---

## actor = "system" for automated events

When the inference worker calls `create_prediction`, there is no human actor. `"system"` is passed as the actor string. Human actions (relabel, role_change) pass the reviewer/admin's email.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `AuditLogDomain` | `app.domain.audit` | ✓ Task 12 |
| `audit_repository` | `app.repositories.audit_repository` | ✓ Task 17 |
| No exceptions raised | — | audit_service never guards |
