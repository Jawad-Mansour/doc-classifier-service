# Decisions

## 1. Queue-backed inference only

The API never runs the classifier directly. All classification requests, including browser uploads, are converted into batch/document records and queued onto Redis/RQ for `inference-worker`. This keeps the HTTP tier responsive and matches the brief's architecture rule.

## 2. Two ingestion paths, one worker pipeline

The repo supports both SFTP ingestion and browser upload, but both feed the same MinIO + RQ + worker path. That keeps persistence, audit, cache invalidation, and model execution logic in one place.

## 3. Persistent auth users in Postgres

User accounts live in Postgres through `fastapi-users`, and Casbin subjects are aligned to `str(user.id)`. This avoids the earlier split-brain problem where JWT identities and RBAC subjects did not match.

## 4. Vault required in local compose

Vault runs in dev mode for the bootcamp stack, but the API still treats it as required infrastructure when `REQUIRE_VAULT=true`. This makes the local demo closer to the brief than silently falling back to plain env secrets.

## 5. Service-layer cache invalidation

Cached reads use `fastapi-cache2`, and invalidation lives in `app/services/` rather than routers or repositories. The namespaces are now aligned across reads and writes:

- `auth:me:{subject}`
- `batches`
- `batch:{batch_id}`
- `predictions:recent`

## 6. Model artifact integrity gate

The classifier artifact is validated against `model_card.json` by SHA-256 before inference. Golden replay also depends on the same shipped artifact, which gives one consistent integrity contract across smoke tests, classifier tests, and demo usage.

## 7. Local-first operational testing

The repo includes a live smoke workflow script instead of relying only on unit tests. It validates compose startup, auth, SFTP ingestion, MinIO, Redis/RQ, prediction persistence, and audit logging end to end on a developer laptop.
