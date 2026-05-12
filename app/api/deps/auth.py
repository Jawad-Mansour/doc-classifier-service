"""
Dependency injection layer.

This module provides:
- Request tracing dependencies
- Current authenticated user dependency
- Database session placeholder
"""

from typing import Annotated

from fastapi import Depends, Header, Request

from app.auth.users import UserRead, current_active_user
from app.services.role_service import RoleService


async def get_request_id(request: Request) -> str:
    """Extract request ID from middleware state."""
    return getattr(request.state, "request_id", "unknown")


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """
    Extract user ID from Authorization header.

    Placeholder: JWT validation will be implemented here.
    """
    if not authorization:
        return None
    # TODO: Implement JWT token validation in a dedicated auth service.
    return None


async def get_db():
    """
    Provide database session.

    Placeholder: DB session management will be implemented here.
    """
    # TODO: Implement DB session management
    yield None


async def get_current_user_with_role(user: UserRead = Depends(current_active_user)) -> UserRead:
    """Attach the user's current RBAC role to the authenticated user object."""
    roles = await RoleService.get_user_roles(str(user.id))
    user.role = roles[0] if roles else None
    return user


# Annotated dependency types for cleaner router signatures
RequestIDDep = Annotated[str, Depends(get_request_id)]
CurrentUserIDDep = Annotated[str | None, Depends(get_current_user_id)]
DBSessionDep = Annotated[None, Depends(get_db)]
CurrentActiveUserDep = Annotated[UserRead, Depends(get_current_user_with_role)]
