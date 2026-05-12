# Task 21 — app/services/prediction_service.py

## What it does

Business logic for predictions. Jad is blocked on `create_prediction()` — it's the function his inference worker calls after the model runs. Contains the relabel guard that enforces `CONFIDENCE_THRESHOLD`.

---

## Functions

### create_prediction(session, job_id, batch_id, document_id, label_id, label, confidence, top5, all_probs, model_sha256, overlay_bucket, overlay_path, request_id) → PredictionDomain

Saves the full inference result. Operation order:
```
1. prediction_repo.create()             → flush
2. audit_service.log_event("system", "prediction_created", "document:{id}")
3. session.commit()
4. cache_service.invalidate_predictions()
5. return PredictionDomain
```

**FLAG FOR JAD:** `all_probs` is required by `prediction_repository.create()`. It is currently missing from his `PredictionResult` in `app/classifier/inference/types.py`. He must add it.

### list_predictions(session, batch_id) → list[PredictionDomain]
Read-only. Returns all predictions for a batch ordered by `created_at` ASC. Ali calls this for `GET /batches/{id}/predictions`.

### get_recent(session, limit=20) → list[PredictionDomain]
Read-only. Returns the `limit` most recent predictions across all batches. Ali calls this for `GET /predictions/recent`. Default limit is 20.

### relabel(session, prediction_id, new_label, reviewer) → PredictionDomain

The relabel guard:
```python
if prediction.confidence >= CONFIDENCE_THRESHOLD:   # 0.7
    raise UnauthorizedRelabel
```

Operation order (after guard passes):
```
1. prediction_repo.get_by_id()          → fetch current row + confidence
2. guard check (confidence >= 0.7 → raise UnauthorizedRelabel)
3. CLASS_NAMES.index(new_label)         → derive new_label_id
4. prediction_repo.update_label()       → flush both label and label_id
5. audit_service.log_event(reviewer, "relabel", "prediction:{id}")
6. session.commit()
7. cache_service.invalidate_predictions()
8. return PredictionDomain
```

---

## Relabel guard direction

The guard fires when `confidence >= 0.7`. This means: high-confidence predictions cannot be relabeled. Only uncertain predictions (confidence < 0.7) can be overridden by a human reviewer. This is intentional per project spec — don't override the model when it's confident.

---

## label_id derivation in relabel

`new_label_id = CLASS_NAMES.index(new_label)` assumes `new_label` is a valid entry in CLASS_NAMES. If it's not, `list.index()` raises `ValueError`. This is intentional — invalid label strings should be caught by Ali's request schema validation before reaching this service. A `ValueError` here indicates a programming error, not a user error.

---

## expire_on_commit=False — why model_validate works after commit

`session.commit()` normally expires all loaded ORM objects. With `expire_on_commit=False` (set in `session.py`), the in-memory `prediction` object retains its values after commit. `PredictionDomain.model_validate(prediction)` works correctly after commit without a re-query.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `PredictionDomain` | `app.domain.prediction` | ✓ Task 11 |
| `PredictionNotFound`, `UnauthorizedRelabel` | `app.exceptions` | ✓ Task 3 |
| `CLASS_NAMES`, `CONFIDENCE_THRESHOLD` | `app.core.constants` | ✓ Task 2 |
| `prediction_repository` | `app.repositories.prediction_repository` | ✓ Task 16 |
| `audit_service` | `app.services.audit_service` | ✓ Task 18 |
| `cache_service` | `app.services.cache_service` | ✓ Task 19 |

## Who calls this

| Caller | Functions |
|---|---|
| Jad's inference_worker | `create_prediction` |
| Ali's predictions router | `list_predictions`, `get_recent`, `relabel` |
