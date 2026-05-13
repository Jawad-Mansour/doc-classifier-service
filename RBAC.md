# RBAC Implementation Guide

This document describes the Role-Based Access Control (RBAC) implementation using Casbin.

## Overview

The document classification API implements three roles with specific permissions:

### Roles

- **admin**: Full access to user management and audit logs
- **reviewer**: Access to batches and predictions (can update with confidence < 0.7)
- **auditor**: Read-only access to batches and audit logs

### Permissions Matrix

| Role | Users | Batches | Predictions | Audit Log |
|------|-------|---------|-------------|-----------|
| admin | CRUD + manage_roles | R | R | R |
| reviewer | - | R | RU* | - |
| auditor | - | R | - | R |

*RU = Read and Update (only confidence < 0.7)

## Architecture

```
app/auth/casbin.py           # Casbin model, enforcer, constants
app/services/role_service.py # Role management (service layer, no SQL)
app/api/deps/permissions.py  # Permission dependency functions
app/api/routers/
  ├── users.py              # Admin-only user management
  ├── batches.py            # Reviewer/auditor batch access
  ├── audit.py              # Read-only audit logs
  └── ...
scripts/seed_policies.py     # Initialize RBAC policies
```

## Usage

### 1. Seed Policies (Startup)

Policies are automatically seeded when the app starts via `init_app()`:

```python
# In app/core/startup.py
async def init_app() -> None:
    await RoleService.seed_default_policies()
```

Or manually:

```bash
python scripts/seed_policies.py
```

### 2. Protect Routes with Dependencies

**Role-based checks:**

```python
from app.api.deps.permissions import require_admin, require_reviewer

@router.get("/users")
async def list_users(user = Depends(require_admin)):
    # Only admins can access
    pass

@router.get("/batches")
async def list_batches(user = Depends(require_reviewer)):
    # Reviewers and admins can access
    pass
```

**Resource-based permission checks (optional):**

```python
from app.api.deps.permissions import require_permission
from app.auth.casbin import RESOURCE_BATCHES, ACTION_READ

@router.get("/batches")
async def list_batches(
    user = Depends(require_permission(RESOURCE_BATCHES, ACTION_READ))
):
    pass
```

### 3. Manage User Roles

**In service layer (no SQL in routers):**

```python
from app.services.role_service import RoleService

# Assign role
await RoleService.assign_role("user_id", "admin")

# Toggle role
await RoleService.toggle_role("user_id", "reviewer")

# Get user roles
roles = await RoleService.get_user_roles("user_id")
```

**In router (calls service):**

```python
@router.post("/users/assign-role")
async def assign_role(
    request: AssignRoleRequest,
    user: CurrentActiveUserDep = Depends(require_admin),
):
    await RoleService.assign_role(request.user_id, request.role)
    return {"message": "Role assigned"}
```

## Constants

Available in `app/auth/casbin.py`:

### Roles
- `ROLE_ADMIN = "admin"`
- `ROLE_REVIEWER = "reviewer"`
- `ROLE_AUDITOR = "auditor"`

### Resources
- `RESOURCE_USERS = "users"`
- `RESOURCE_BATCHES = "batches"`
- `RESOURCE_PREDICTIONS = "predictions"`
- `RESOURCE_AUDIT_LOG = "audit_log"`

### Actions
- `ACTION_CREATE = "create"`
- `ACTION_READ = "read"`
- `ACTION_UPDATE = "update"`
- `ACTION_DELETE = "delete"`
- `ACTION_MANAGE_ROLES = "manage_roles"`

## Testing

### Unit Tests

Test permission enforcement:

```bash
pytest tests/test_rbac_permissions.py
```

Tests cover:
- Role permission matrices
- Role hierarchy (admin > reviewer > auditor)
- RoleService operations (assign, toggle, get)
- Permission denial for unauthorized roles

### Route Protection Tests

Test protected endpoints:

```bash
pytest tests/test_route_protection.py
```

Template tests for:
- Admin-only routes
- Reviewer/auditor access
- Unauthenticated denial

## Key Design Decisions

### No SQL in Routers
- All role/permission operations go through `RoleService`
- `RoleService` handles Casbin operations
- Routers use clean dependency injection for permission checks

### Casbin Model
- RBAC model with role hierarchies (g = _, _)
- Policies stored in database via SQLAlchemy adapter
- Async enforcer for FastAPI compatibility

### Separation of Concerns
- `casbin.py`: Model, enforcer, constants
- `role_service.py`: Business logic for roles
- `permissions.py`: FastAPI dependencies for route protection
- `routers/`: Thin endpoint handlers (no business logic)

## Startup Check

The app fails at startup if policies are not initialized:

```python
async def check_policies_initialized() -> None:
    """Check that RBAC policies are initialized."""
    enforcer = await get_casbin_enforcer()
    policies = await enforcer.get_policy()
    
    if not policies:
        raise RuntimeError(
            "RBAC policies table is empty. "
            "Please run: python scripts/seed_policies.py"
        )
```

## Dependencies

Required packages (already in `requirements.txt`):
- `casbin==1.43.0`
- `casbin-sqlalchemy-adapter==1.4.0`
- `fastapi`
- `sqlalchemy`

## Future Extensions

1. **Dynamic Policy Updates**: Add admin endpoints to manage policies at runtime
2. **Attribute-Based Access Control (ABAC)**: Extend Casbin model for attribute-based rules
3. **Audit Logging**: Log all permission checks and role changes
4. **Permission Caching**: Cache permission checks for performance
