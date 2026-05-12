"""Permission and role-based access control dependencies."""

from typing import Callable
from fastapi import Depends, HTTPException, status

from app.auth.casbin import (
    get_casbin_enforcer,
    ROLE_ADMIN,
    ROLE_REVIEWER,
    ROLE_AUDITOR,
)
from app.api.deps.auth import CurrentActiveUserDep


def require_role(*roles: str) -> Callable:
    """Factory: return a FastAPI dependency that enforces one of the given roles."""
    async def check_role(user: CurrentActiveUserDep) -> CurrentActiveUserDep:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' not authorized. Required: {roles}",
            )
        return user

    return check_role


def require_permission(resource: str, action: str) -> Callable:
    """Factory: return a FastAPI dependency that enforces a Casbin resource+action policy."""
    async def check_permission(user: CurrentActiveUserDep) -> CurrentActiveUserDep:
        enforcer = get_casbin_enforcer()
        if not enforcer.enforce(user.role, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' cannot {action} {resource}",
            )
        return user

    return check_permission


def require_admin(user: CurrentActiveUserDep) -> CurrentActiveUserDep:
    """Require admin role."""
    if user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user


def require_reviewer(user: CurrentActiveUserDep) -> CurrentActiveUserDep:
    """Require reviewer role or higher."""
    if user.role not in (ROLE_ADMIN, ROLE_REVIEWER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer role required",
        )
    return user


def require_auditor(user: CurrentActiveUserDep) -> CurrentActiveUserDep:
    """Require any authenticated user (all roles have read access)."""
    return user
