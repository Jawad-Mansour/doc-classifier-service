"""Admin user management routes."""

from fastapi import APIRouter, Depends, Path

from app.api.deps.permissions import require_admin
from app.api.schemas import UserRoleResponse, UserRoleUpdateRequest
from app.auth.users import UserRead
from app.services.user_service import change_role

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.patch("/{id}/role", response_model=UserRoleResponse)
async def change_user_role(
    request: UserRoleUpdateRequest,
    id: str = Path(...),
    user: UserRead = Depends(require_admin),
) -> UserRoleResponse:
    """Change the role assigned to a user."""
    return await change_role(id, request.role)
