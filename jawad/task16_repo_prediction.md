# Task 16 — app/repositories/prediction_repository.py

## What it does

SQL-only functions for the `predictions` table. The most field-heavy repo in the project — prediction rows carry all of Jad's inference output.

---

## Functions

| Function | Returns |
|---|---|
| `create(session, job_id, batch_id, document_id, label_id, label, confidence, top5, all_probs, model_sha256, overlay_bucket, overlay_path, request_id)` | `Prediction` |
| `get_by_id(session, prediction_id)` | `Prediction \| None` |
| `list_by_batch_id(session, batch_id)` | `list[Prediction]` ordered by `created_at` ASC |
| `get_recent(session, limit)` | `list[Prediction]` ordered by `created_at` DESC |
| `update_label(session, prediction_id, new_label_id, new_label, relabeled_by)` | `Prediction \| None` |

---

## `create()` — `relabeled_by` is always `None`

New predictions come from the model, not a human. `relabeled_by=None` is set explicitly in the repo. After a human relabels, `update_label()` sets it to their email.

---

## `update_label()` — updates both `label_id` and `label`

These two columns are always in sync: `label = CLASS_NAMES[label_id]`. The repo accepts both because it must write both. The service computes `new_label_id = CLASS_NAMES.index(new_label)` before calling this.

The task description shows `update_label(session, prediction_id, new_label, relabeled_by)` without `new_label_id`. That's incomplete — keeping both columns in sync requires both values.

---

## `get_recent` vs `list_by_batch_id`

- `get_recent(limit)` — no filter, newest-first, used for `GET /predictions/recent`
- `list_by_batch_id(batch_id)` — filtered by batch, oldest-first (natural processing order), used for `GET /batches/{id}/predictions`

---

## `top5` and `all_probs` JSON columns

Stored as-is from Jad's model output. No serialization needed — SQLAlchemy's JSON column type handles Python list/dict ↔ Postgres JSON automatically.

FLAG FOR JAD: `all_probs` must be included in his `PredictionResult` (currently missing from `app/classifier/inference/types.py`). The `create()` signature requires it.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `Prediction` | `app.db.models` | ✓ Task 4 |
| `AsyncSession` | `sqlalchemy.ext.asyncio` | ✓ |

## Who calls this

Only `app/services/prediction_service.py`.
