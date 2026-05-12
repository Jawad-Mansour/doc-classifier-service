"""Authentication router."""

from fastapi import APIRouter, Depends

from app.api.deps.auth import get_current_user_with_role
from app.auth.users import UserRead, auth_router, register_router

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(register_router, prefix="", tags=["auth"])
router.include_router(auth_router, prefix="", tags=["auth"])


@router.get("/me", response_model=UserRead)
async def read_current_user(user: UserRead = Depends(get_current_user_with_role)) -> UserRead:
    """Return the current authenticated user."""
    return user
