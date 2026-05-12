# Task 2 — app/core/constants.py

## What it does

Defines all shared constant values used across the service layer, ORM models, and domain models. One source of truth for the confidence threshold, the 16 RVL-CDIP class names (with their integer IDs), the batch status states, and the user roles.

## Code decisions

**CONFIDENCE_THRESHOLD = 0.7**
Defined in the project spec (project-6.pdf): reviewers may only relabel predictions where top-1 confidence < 0.7. Used in `prediction_service.relabel()` as the guard condition.

**CLASS_NAMES**
Copied exactly from `app/classifier/models/model_card.json` — Jad's artifact. The index position IS the label_id (0=letter, 1=form, ..., 15=memo). This order must never change because Jad's model output uses these indices. The comment on each line makes the mapping explicit.

**BatchStatus(str, Enum)**
`str` mixin allows SQLAlchemy to store the value as a plain string in the DB column and Pydantic to serialize it directly without extra conversion. The four states cover the full lifecycle of a batch: created → queued → done or failed.

**UserRole(str, Enum)**
Three roles from the project spec: admin, reviewer, auditor. Same `str` mixin for the same reason. Used in the User ORM model and domain model. Ali's Casbin policies reference these role strings — they must match exactly.

## Approach and defense

No over-engineering. This file has no logic, no imports beyond the standard library, and no classes beyond what the spec explicitly requires. A plain `list[str]` for CLASS_NAMES is correct — there is no need for a mapping class or a lookup function here.

## Who depends on this

| Who | File | What they use |
|---|---|---|
| Mohamad (Task 4) | app/db/models.py | `BatchStatus` for Batch.status column type, `UserRole` for User.role column type |
| Mohamad (Task 9) | app/domain/batch.py | `BatchStatus` in BatchDomain.status field |
| Mohamad (Task 8) | app/domain/user.py | `UserRole` in UserDomain.role field |
| Mohamad (Task 21) | app/services/prediction_service.py | `CONFIDENCE_THRESHOLD` in relabel() guard |
| Jad | app/workers/inference_worker.py | `CLASS_NAMES` — must match model output indices exactly |
| Ali | app/auth/casbin.py | `UserRole` values must match Casbin policy strings |

## Critical contract with Jad

The `CLASS_NAMES` list index must match the `label_id` that Jad's model outputs.
Verified against `app/classifier/models/model_card.json`:
- The model card lists classes in the same order
- Jad's postprocessing.py uses `class_names[index]` to map logit index → label string
- **Do not reorder this list**
