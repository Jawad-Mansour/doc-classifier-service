# Security Notes

## Production hardening

- `SECRET_KEY` must be configured in environment and must not be the default placeholder.
- `ALLOWED_ORIGINS` must not include wildcard origins in production.
- CORS is restricted to configured origins only.
- Default headers enforce `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `X-XSS-Protection`.

## Error handling

- All errors return structured JSON with `request_id`.
- Internal server errors do not expose stack traces or internal exception details.
- Validation errors return safe, structured validation details.

## Request tracing

- Each request receives a unique `X-Request-ID` header.
- Request ID is propagated into logs through a logging filter.
- The request ID is also included in error responses for support correlation.

## Startup checks

- The app validates security configuration at startup.
- RBAC policy initialization is checked so the API does not start in an incomplete state.

## No secret leakage

- No application secrets or stack traces are returned to clients.
- Logs and responses only expose the request identifier for support correlation.
