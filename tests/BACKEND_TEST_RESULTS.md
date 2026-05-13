# Backend Test Results

Date: 2026-05-13

## Scope

Backend-only pass for:

- Auth/RBAC 403 alignment
- Vault local dev requirement
- Cache namespace contract
- UI handoff demo users
- Batch lifecycle status updates

Not changed in this pass:

- Classifier model artifacts
- Classifier metrics
- Golden images
- Training artifacts
- UI

## RBAC Result

Protected API dependencies use the authenticated FastAPI Users Postgres user id as the Casbin subject:

```text
subject = str(user.id)
```

Auth users are persisted in the `users` table. Role assignment writes both:

```text
users.role
Casbin g policy for str(users.id)
```

Stable admin role endpoint:

```text
PATCH /api/v1/admin/users/{id}/role
```

Local demo seeding is guarded by:

```text
DEBUG=true
SEED_DEMO_USERS=true
```

Seeded demo accounts:

```text
admin@example.com / Admin123!       role=admin
reviewer@example.com / Reviewer123! role=reviewer
auditor@example.com / Auditor123!   role=auditor
```

Verified access:

```text
admin    GET /api/v1/audit-log           200
reviewer GET /api/v1/batches             200
reviewer GET /api/v1/predictions/recent  200
reviewer GET /api/v1/audit-log           403
auditor  GET /api/v1/batches             200
auditor  GET /api/v1/audit-log           200
auditor  GET /api/v1/predictions/recent  403
```

## Vault Result

Vault runs in Docker dev mode:

```text
service: vault
image: hashicorp/vault
command: server -dev
VAULT_DEV_ROOT_TOKEN_ID=root
VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
```

The API requires Vault in Compose and reads/seeds:

```text
VAULT_URL=http://vault:8200
VAULT_SECRET_BASE_PATH=secret/data/doc-classifier
fields=jwt_secret_key,database_password,minio_secret_key,sftp_password
```

Host health check passed:

```text
GET http://localhost:8200/v1/sys/health -> 200
```

API startup confirmed:

```text
GET http://vault:8200/v1/sys/health -> 200
GET http://vault:8200/v1/secret/data/doc-classifier -> 200
```

## Cache Contract

Route cache namespaces:

```text
GET /api/v1/auth/me             auth:me:{subject}
GET /api/v1/batches             batches
GET /api/v1/batches/{bid}       batch:{bid}
GET /api/v1/predictions/recent  predictions:recent
```

Invalidation namespaces:

```text
Batch create/update/document add: batches, batch:{batch_id}
Prediction create/relabel:       predictions:recent, batches, batch:{batch_id}
Role change:                     auth:me:{subject}
```

## Batch Lifecycle Result

Batch status updates:

```text
SFTP enqueue:       processing
Inference success:  done
Inference failure:  failed
```

Status transitions use `batch_service.update_status`, which also audits `status_change` and invalidates `batches` plus `batch:{batch_id}`.

## Commands Run

Docker/config:

```bash
docker compose config
DEBUG=true SEED_DEMO_USERS=true docker compose up -d --build
DEBUG=true SEED_DEMO_USERS=true docker compose up -d --force-recreate api
```

Backend tests:

```bash
docker compose run -e REQUIRE_VAULT=false -e SEED_DEMO_USERS=false --rm inference-worker python -m py_compile app/auth/users.py app/api/routers/auth.py app/api/routers/batches.py app/api/routers/predictions.py app/core/config.py app/core/security.py app/core/startup.py app/infra/vault/vault_client.py app/services/cache_service.py app/services/batch_service.py app/services/prediction_service.py
docker compose run -e REQUIRE_VAULT=false -e SEED_DEMO_USERS=false --rm inference-worker python -m pytest tests/smoke tests/infra tests/api tests/test_rbac_permissions.py tests/test_route_protection.py
docker compose run --rm inference-worker python -m pytest --noconftest tests/classifier
docker compose run --rm inference-worker python app/classifier/eval/golden.py
docker compose run -e REQUIRE_VAULT=false -e SEED_DEMO_USERS=false --rm inference-worker python -m pytest --ignore=tests/e2e
docker compose run -e REQUIRE_VAULT=false -e SEED_DEMO_USERS=false --rm inference-worker python -m pytest tests/infra/test_config.py tests/infra/test_vault_client.py tests/api/test_auth_permissions.py
docker compose run -e REQUIRE_VAULT=false -e SEED_DEMO_USERS=false --rm inference-worker python -m pytest tests/infra/test_sftp_ingest_worker.py tests/services/test_batch_service.py tests/classifier/test_inference_worker.py --noconftest
```

Health/API checks:

```text
GET http://localhost:8000/api/v1/health -> 200
GET http://localhost:8000/api/v1/ready -> 200
GET http://localhost:8000/api/docs -> 200
GET http://localhost:8200/v1/sys/health -> 200
GET http://localhost:8200/v1/secret/data/doc-classifier -> 200
POST /api/v1/auth/login demo users -> 200
GET /api/v1/auth/me demo users -> 200 with roles
PATCH /api/v1/admin/users/{id}/role -> 200 and updates /auth/me role
API restart -> demo users can still log in from Postgres
```

## Test Results

```text
py_compile: passed
targeted auth/RBAC/Vault/user-service: 41 passed
smoke + infra + api + RBAC/protection: 45 passed
classifier tests without root conftest: 5 passed
golden replay: passed, 50 images
non-e2e full suite: 63 passed
batch lifecycle targeted tests: 6 passed
```

## Remaining Notes

The demo users are persisted in Postgres and reseeded idempotently on API startup only when `DEBUG=true` and `SEED_DEMO_USERS=true`.

For a faster local restart after code-only changes, use:

```bash
DEBUG=true SEED_DEMO_USERS=true docker compose up -d --force-recreate api
```
