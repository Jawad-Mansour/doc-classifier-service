# Task 9 — app/domain/batch.py

## What it does

Defines `BatchDomain`, a Pydantic model representing a processing batch as returned by the service layer. Services convert `Batch` ORM rows to this model before returning to routers. Routers use this for response serialization.

---

## Design decisions

### `status: str` not `status: BatchStatus`
ORM stores status as a plain string. Keeping `str` here avoids a coercion step. `BatchStatus` enum is used in service logic for comparisons (`if batch.status == BatchStatus.DONE`), not for the domain model type annotation.

### `created_at: datetime`
Stored as timezone-aware datetime in Postgres (`DateTime(timezone=True)`). Pydantic serializes it as ISO-8601 with timezone offset by default — correct for API responses.

### No `documents` list
`BatchDomain` does not embed a list of documents. Routers that need batch + documents call two service methods and compose them. Avoids N+1 query footguns and keeps the model flat.

---

## Usage pattern

```python
from app.db.models import Batch as BatchORM
from app.domain.batch import BatchDomain

orm_row: BatchORM = await session.get(BatchORM, batch_id)
domain: BatchDomain = BatchDomain.model_validate(orm_row)
return domain
```

---

## Who uses this

| Who | Where | What they need |
|---|---|---|
| Ali | `app/api/routers/batches.py` | Return type for `GET /batches/{id}`, `POST /batches` |
| Mohamad | `app/services/batch_service.py` | Return type from `get_batch()`, `create_batch()`, `update_status()` |
| Mohamad | `app/repositories/batch_repo.py` | Output of `get_by_id()`, `create()` |
| Jad's worker | RQ job result | Needs `batch_id` from `BatchDomain.id` to record predictions |

---

## Status lifecycle

```
pending → processing → done
                    ↘ failed
```

Every status transition is audit-logged by `batch_service.update_status()`. The domain model carries the current status string — transition logic lives in the service, not here.
