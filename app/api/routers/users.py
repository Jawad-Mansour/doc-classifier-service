"""Admin user management routes."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.permissions import require_admin
from app.api.schemas import UserRoleResponse, UserRoleUpdateRequest
from app.auth.users import UserRead
from app.db.session import get_session
from app.exceptions import LastAdminError, UserNotFound
from app.services.user_service import toggle_role

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.patch("/{id}/role", response_model=UserRoleResponse)
async def change_user_role(
    request: UserRoleUpdateRequest,
    id: int = Path(...),
    user: UserRead = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> UserRoleResponse:
    try:
        return await toggle_role(session, id, request.role, user.email)
    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")
    except LastAdminError:
        raise HTTPException(status_code=400, detail="Cannot demote the last admin")
