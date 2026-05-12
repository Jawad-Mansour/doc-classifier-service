# Task 10 — app/domain/document.py

## What it does

Defines `DocumentDomain`, a Pydantic model representing a single uploaded document as returned by the service layer. Created new — this file did not exist in the repo skeleton.

---

## Design decisions

### `blob_bucket` + `blob_path` included
Routers that serve document download links need the MinIO coordinates to generate presigned URLs. Both fields are exposed in the domain model. The router calls MinIO's presign API with these values — the domain model is the data carrier, not the URL generator.

### No `prediction` embedded
A document's prediction is a separate resource (`predictions` table, separate FK). The domain model stays flat. Routers needing document + prediction fetch them independently via their respective services.

### `batch_id` included
The document always belongs to a batch. `batch_id` is included for the common case where a router has a `DocumentDomain` and needs to know which batch it belongs to, without a second DB query.

### File created new (was missing from skeleton)
The repo had `user.py`, `batch.py`, `prediction.py`, and `audit.py` as empty stubs. `document.py` was absent. Created it here.

---

## Usage pattern

```python
from app.db.models import Document as DocumentORM
from app.domain.document import DocumentDomain

orm_row: DocumentORM = await session.get(DocumentORM, document_id)
domain: DocumentDomain = DocumentDomain.model_validate(orm_row)
return domain
```

---

## Who uses this

| Who | Where | What they need |
|---|---|---|
| Ali | `app/api/routers/documents.py` | Return type for `GET /batches/{id}/documents` |
| Mohamad | `app/services/document_service.py` | Return type from `get_document()`, `list_by_batch()`, `add_document()` |
| Mohamad | `app/repositories/document_repo.py` | Output of `get_by_id()`, `list_by_batch_id()`, `create()` |
| Jad's RQ worker | job payload | Worker uses `document_id` and `blob_path` to fetch the file from MinIO for inference |

---

## MinIO coordinate usage

The `blob_bucket` and `blob_path` fields together form the MinIO object reference:
- `blob_bucket`: bucket name (e.g. `"documents"`)
- `blob_path`: object key within the bucket (e.g. `"batches/42/invoice.pdf"`)

The router or worker calls `minio_client.presigned_get_object(blob_bucket, blob_path)` to generate a download URL or `minio_client.get_object(blob_bucket, blob_path)` to stream the bytes directly.
