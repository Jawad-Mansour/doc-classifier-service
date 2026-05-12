# Task 20 — app/services/batch_service.py

## What it does

Business logic for batches and documents. The first service Aya depends on — she calls `create_batch()` and `add_document()` before pushing the Redis inference job. Jad calls `update_status()` after inference completes.

---

## Functions

### create_batch(session, request_id) → BatchDomain
Creates a batch with `status="pending"`. Commits immediately — Aya needs the `batch.id` synchronously before she can push the Redis job.

### add_document(session, batch_id, filename, blob_bucket, blob_path) → DocumentDomain
Creates a document row. Commits immediately. Aya reads `document.id` from the returned `DocumentDomain` and puts it in the Redis job payload:
```python
doc = await batch_service.add_document(session, batch_id, ...)
job_payload = {"batch_id": batch_id, "document_id": doc.id, ...}
```
**The `doc.id` must be populated on return** — guaranteed by the `flush() + refresh()` in `document_repository.create()`.

### get_batch(session, batch_id) → BatchDomain
Read-only. Raises `BatchNotFound` if the batch doesn't exist. Ali uses this for `GET /batches/{id}`.

### list_batches(session) → list[BatchDomain]
Read-only. Returns all batches newest-first (ordering is in the repo layer).

### update_status(session, batch_id, status) → BatchDomain
Write + audit + cache invalidation. Operation order:
```
1. batch_repo.update_status()       → flush
2. audit_service.log_event()        → flush (same transaction)
3. session.commit()                 → both changes committed atomically
4. cache_service.invalidate_batch() → clears stale cache (after commit)
5. return BatchDomain
```
Raises `BatchNotFound` if batch doesn't exist (checked before audit/commit).

---

## Status transitions

No transition validation in the service — any status string is accepted. If transition logic (e.g., can't go from "done" back to "pending") is required, add it here before the repo call. For now the project doesn't specify restrictions.

---

## No audit on create_batch or add_document

project-6.pdf only requires audit for: batch status changes, relabels, role changes. Creation events are not audited.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `BatchDomain` | `app.domain.batch` | ✓ Task 9 |
| `DocumentDomain` | `app.domain.document` | ✓ Task 10 |
| `BatchNotFound` | `app.exceptions` | ✓ Task 3 |
| `batch_repository` | `app.repositories.batch_repository` | ✓ Task 14 |
| `document_repository` | `app.repositories.document_repository` | ✓ Task 15 |
| `audit_service` | `app.services.audit_service` | ✓ Task 18 |
| `cache_service` | `app.services.cache_service` | ✓ Task 19 |

## Who calls this

| Caller | Functions |
|---|---|
| Aya's sftp_ingest_worker | `create_batch`, `add_document` |
| Jad's inference_worker | `update_status` |
| Ali's batches router | `get_batch`, `list_batches` |
