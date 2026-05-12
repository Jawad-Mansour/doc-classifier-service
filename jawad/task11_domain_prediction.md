# Task 11 — app/domain/prediction.py

## What it does

Defines `PredictionDomain`, a Pydantic model representing a single inference result as returned by the service layer. This is the central data contract between Mohamad's services and Ali's routers — and the output format that Jad's RQ worker must produce when calling `prediction_service.record_prediction()`.

---

## Field-by-field rationale

| Field | Type | Why |
|---|---|---|
| `label_id` | `int` | Index into `CLASS_NAMES`. Matches Jad's model output directly. |
| `label` | `str` | Human-readable class name. Denormalized from `CLASS_NAMES[label_id]` at write time. |
| `confidence` | `float` | Raw softmax score for the top class. Used by relabel guard (`< CONFIDENCE_THRESHOLD` → reject). |
| `top5` | `list[Any]` | Top-5 predictions from Jad's model. Structure: list of dicts with `label` and `confidence` keys. Typed `Any` to avoid breakage if Jad adjusts the inner structure. |
| `all_probs` | `dict[str, Any]` | Full softmax distribution keyed by class name. Used for the probability bar chart in the UI. |
| `model_sha256` | `str` | 64-char hex SHA-256 of the model weights file. Audit trail — tells you exactly which checkpoint produced this result. |
| `overlay_bucket` | `str` | MinIO bucket for Jad's GradCAM overlay image. |
| `overlay_path` | `str` | MinIO object key for GradCAM overlay. Router generates a presigned URL from these two fields. |
| `relabeled_by` | `str \| None` | `None` = model-generated prediction. Non-null = email of the reviewer who overrode the label. |
| `job_id` | `str` | RQ job ID. Used for tracing a prediction back to the specific worker job that produced it. |
| `request_id` | `str` | Propagated from the batch's `request_id`. Ties the prediction back to the original upload request. |

---

## `top5` vs `all_probs` typing

Both are JSON columns. `top5` is a list (ordered, top-5 only), `all_probs` is a dict (keyed by class name, all 16 classes). Using `list[Any]` and `dict[str, Any]` rather than fully typed nested models keeps this domain model stable if Jad tweaks the inner structure during development.

FLAG FOR JAD: `all_probs` is present in the ORM model and this domain model but was missing from his `PredictionResult` type in `types.py`. He must add it before `record_prediction()` is called.

---

## Relabel guard contract

The service that handles relabeling (`prediction_service.relabel()`) checks:
```python
if prediction.confidence < CONFIDENCE_THRESHOLD:
    raise UnauthorizedRelabel
```
`confidence` is included in the domain model precisely so this check works without a second DB query.

---

## Who uses this

| Who | Where | What they need |
|---|---|---|
| Ali | `app/api/routers/predictions.py` | Return type for `GET /predictions/{id}`, `GET /batches/{id}/predictions` |
| Ali | relabel endpoint | Input validation + response |
| Jad | RQ worker | Must populate ALL fields when calling `record_prediction()` |
| Mohamad | `app/services/prediction_service.py` | Return type from `get_prediction()`, `list_by_batch()`, `record_prediction()`, `relabel()` |
| Mohamad | `app/repositories/prediction_repo.py` | Output of `get_by_id()`, `list_by_batch_id()`, `create()`, `update_label()` |
