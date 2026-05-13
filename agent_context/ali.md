# Ali

## Scope
- API, auth, permissions, Casbin, routes

## Completed
- Built FastAPI auth layer using `fastapi-users` and JWT backend plumbing
- Added Casbin RBAC model and role permission definitions for admin/reviewer/auditor
- Implemented API routers for health, auth, users, batches, predictions, and audit
- Added request ID middleware and response propagation
- Added structured error handling and startup security validation
- Implemented role-based dependencies and permission checks in `app/api/deps/permissions.py`
- Enforced admin-only user role changes and reviewer/auditor batch/prediction access
- Created focused test scaffolding for auth/permissions routes using mocked services
- Fixed Casbin compatibility by switching to synchronous `casbin.Enforcer`
- Updated `current_active_user` enrichment so authenticated users receive assigned role data
- Corrected API schema exports in `app/api/schemas/__init__.py` to resolve import errors

## Files changed
- `app/auth/users.py`
- `app/auth/casbin.py`
- `app/api/deps/auth.py`
- `app/api/deps/permissions.py`
- `app/api/routers/auth.py`
- `app/api/routers/audit.py`
- `app/api/schemas/__init__.py`
- `app/api/routers/users.py`
- `app/api/routers/batches.py`
- `app/api/routers/predictions.py`
- `app/core/startup.py`
- `app/services/role_service.py`
- `tests/api/test_auth_permissions.py`

## How to test
- Run `py_compile` on the modified Python files
- Run focused pytest for auth/permissions once dependencies are installed
- Start the app and verify the auth flow, `/auth/me`, `/audit-log`, and RBAC-protected endpoints

## Blocked
- Full runtime verification until `fastapi-users` and environment dependencies are installed

## Contracts needed
- Ensure Casbin policy seeding is available before startup
- Ensure user role persistence and retrieval from auth/user store

## Caveats / known limitations
- `get_current_user_id` remains a placeholder and does not perform manual JWT parsing
- Current implementation assumes role info is available via Casbin roles and attached to the user object

## Next steps
- Add regression tests for RBAC permission enforcement and audit log access
- Remove legacy `app/api/schemas.py` module to prevent package import confusion
- Complete JWT auth validation and real user persistence logic
