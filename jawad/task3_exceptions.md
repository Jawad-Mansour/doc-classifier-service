# Task 3 — app/exceptions.py

## What it does

Defines all custom domain exception classes for the service layer. When a business rule is violated or a record is not found, a service raises one of these exceptions. Ali's routers catch them and return the correct HTTP response. Without these, every failure in a service would surface as an unhandled Python exception and the API would return HTTP 500 for every error.

## The exceptions and why each exists

### `UserNotFound`
Raised by `user_service` when `user_repository.get_by_id()` or `user_repository.get_by_email()` returns `None`. This happens when Ali's router tries to fetch a user that does not exist in the database — for example when an admin calls `PATCH /admin/users/{id}/role` with an id that does not exist.

**Ali maps this to: HTTP 404**

---

### `BatchNotFound`
Raised by `batch_service` when `batch_repository.get_by_id()` returns `None`. This happens when Ali's router calls `GET /batches/{bid}` or `batch_service.update_status()` is called with an id that does not exist in the database.

**Ali maps this to: HTTP 404**

---

### `DocumentNotFound`
Raised by `batch_service.add_document()` if the provided `batch_id` references a batch that does not exist, or by any lookup that tries to find a document by id that is not in the database. This exception also protects the pipeline — if Jad's worker receives a `document_id` in the Redis job that does not resolve to a real row, this exception is raised before a bad prediction is saved.

**Ali maps this to: HTTP 404**

---

### `PredictionNotFound`
Raised by `prediction_service.relabel()` when the `prediction_id` passed by Ali's router does not exist in the database. Ali calls `PATCH /predictions/{id}` — if that prediction row is missing, this is raised before any DB write happens.

**Ali maps this to: HTTP 404**

---

### `LastAdminError`
Raised by `user_service.toggle_role()` when the system detects that the user being demoted is the only remaining admin. The project spec (project-6.pdf, "Think About" section) explicitly requires this guard: *"What happens when the only admin tries to demote themselves?"* — the answer is: it must be blocked at the service level.

The logic in `user_service`: count all users with `role = admin`. If the count is 1 and the target user is that admin, raise `LastAdminError` before touching the database. This guarantees the system can never reach a state with zero admins.

**Ali maps this to: HTTP 400** (bad request — the action is syntactically valid but violates a business rule)

---

### `UnauthorizedRelabel`
Raised by `prediction_service.relabel()` when a reviewer attempts to relabel a prediction whose `confidence >= CONFIDENCE_THRESHOLD (0.7)`. The project spec states: *"reviewer: relabel predictions where top-1 confidence < 0.7"*. High-confidence predictions are considered reliable enough that manual relabeling is not permitted.

The logic in `prediction_service`: fetch the prediction, check `prediction.confidence >= CONFIDENCE_THRESHOLD`, raise `UnauthorizedRelabel` before any DB write if the guard fails.

**Ali maps this to: HTTP 403** (forbidden — the user has the right role but the action is not permitted on this specific record)

---

## Approach and defense

Every exception is a plain subclass of `Exception` with no constructor arguments, no message, no extra fields. This is intentional.

The reason is the layered architecture rule: services raise, routers catch. The router knows the context (which endpoint was called, what the user intended) better than the service does. If `LastAdminError` carried a message, the service would be making decisions about HTTP response text — which belongs in the API layer, not the service layer. Keeping exceptions as empty signal classes keeps the boundary clean.

No inheritance hierarchy between the exceptions either (e.g., no `BaseServiceError` parent). There is no shared behavior to inherit and a hierarchy would add indirection with zero benefit.

## Who raises these

| Exception | Raised by | In response to |
|---|---|---|
| `UserNotFound` | user_service | get_by_id / get_by_email returns None |
| `BatchNotFound` | batch_service | get_by_id returns None |
| `DocumentNotFound` | batch_service | batch or document not found on lookup |
| `PredictionNotFound` | prediction_service | relabel called with unknown prediction_id |
| `LastAdminError` | user_service.toggle_role() | only admin tries to demote themselves |
| `UnauthorizedRelabel` | prediction_service.relabel() | confidence >= 0.7 |

## Who catches these

| Exception | Caught by | HTTP code returned |
|---|---|---|
| `UserNotFound` | Ali — routers/users.py | 404 |
| `BatchNotFound` | Ali — routers/batches.py | 404 |
| `DocumentNotFound` | Ali — routers/batches.py | 404 |
| `PredictionNotFound` | Ali — routers/predictions.py | 404 |
| `LastAdminError` | Ali — routers/users.py | 400 |
| `UnauthorizedRelabel` | Ali — routers/predictions.py | 403 |

## Note to Ali

Import these from `app.exceptions` in your routers. Wrap service calls in try/except blocks and return `JSONResponse` or raise `HTTPException` with the correct status code listed above. Example pattern:

```python
from app.exceptions import BatchNotFound

try:
    batch = await batch_service.get_batch(session, batch_id)
except BatchNotFound:
    raise HTTPException(status_code=404, detail="Batch not found")
```
