# Security

## Auth and RBAC

- Authentication uses `fastapi-users` with email/password registration and JWT bearer tokens.
- JWT signing configuration is loaded at startup and is replaced from Vault when `REQUIRE_VAULT=true`.
- Authorization uses Casbin with three roles:
  - `admin`: user role management, predictions read/update, batches read, audit read
  - `reviewer`: predictions read/update, batches read
  - `auditor`: batches read, audit read
- Role changes are persisted and affect the same subject identity used by JWT auth: `str(user.id)`.

## Secret Handling

- Local compose uses HashiCorp Vault dev mode and the API refuses startup when Vault is required but unreachable.
- Startup reads or seeds the secret path `secret/data/doc-classifier`.
- Current required secret fields are:
  - `jwt_secret_key`
  - `database_password`
  - `minio_secret_key`
  - `sftp_password`
- `.env.example` is intentionally limited to the Vault token and host-published ports. Service-level secret defaults remain in `docker-compose.yml` for local demo bootstrap only.

## HTTP Protections

- `RequestIDMiddleware` issues or propagates `X-Request-ID`.
- `SecurityHeadersMiddleware` adds baseline browser hardening headers.
- CORS is configured from `ALLOWED_ORIGINS` and rejects wildcard origins outside debug mode.
- Structured JSON error responses avoid leaking stack traces to clients.

## Startup Refusal Conditions

The app is designed to fail closed in several important cases:

- Vault is required but unreachable
- Vault is reachable but missing required secret fields
- Casbin policy table is empty
- Security settings are invalid for non-debug mode
- Classifier weights or model-card SHA validation fails before inference

## Audit and Traceability

- Role changes, relabel actions, prediction creation, and batch status changes are written to the audit log.
- Request identifiers are returned in response headers and flow into logs for correlation.
- The live smoke workflow also verifies audit-log writes for the SFTP ingestion path.

## Known Gaps

These matter for the brief audit:

- The strict brief rule `grep -ri 'password' app/` is not yet satisfied. Password-related identifiers still exist in config, auth, repository, and infra code.
- Vault is configured in dev mode, which is appropriate for this bootcamp stack but not for production.
- Demo credentials are enabled in debug mode for local presentation convenience and must not be treated as production practice.
