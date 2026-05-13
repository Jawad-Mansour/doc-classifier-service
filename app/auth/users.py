"""FastAPI Users authentication models and SQLAlchemy adapters."""

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, Authenticator, BearerTransport
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.manager import IntegerIDMixin
from fastapi_users.password import PasswordHelper
from fastapi_users.router import get_auth_router, get_register_router
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_jwt_strategy
from app.core.constants import UserRole
from app.core.security import security_settings
from app.db.models import User as UserDB
from app.db.session import get_session
from app.services import cache_service
from app.services.role_service import RoleService


class UserRead(BaseUser[int]):
    role: str | None = None


class UserCreate(BaseUserCreate):
    pass


class UserUpdate(BaseUserUpdate):
    pass


User = UserRead


class UserManager(IntegerIDMixin, BaseUserManager[UserDB, int]):
    reset_password_token_secret = security_settings.SECRET_KEY
    verification_token_secret = security_settings.SECRET_KEY

    async def on_after_register(self, user: UserDB, request: Any | None = None) -> None:
        """Hook executed after user registration."""
        role = getattr(user, "role", None) or UserRole.AUDITOR.value
        await RoleService.assign_role(str(user.id), role)
        await cache_service.invalidate_auth_user(str(user.id))
        return None


pwd_helper = PasswordHelper()


async def get_user_db(session: AsyncSession = Depends(get_session)) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, UserDB)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db, pwd_helper)


bearer_transport = BearerTransport(tokenUrl="/api/v1/auth/login")
jwt_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

request_authenticator = Authenticator([jwt_backend], get_user_manager)

register_router = get_register_router(get_user_manager, UserRead, UserCreate)
auth_router = get_auth_router(jwt_backend, get_user_manager, request_authenticator)
current_active_user = request_authenticator.current_user(active=True)

fastapi_users = FastAPIUsers(get_user_manager, [jwt_backend])

__all__ = [
    "auth_router",
    "current_active_user",
    "fastapi_users",
    "register_router",
    "User",
    "UserCreate",
    "UserDB",
    "UserUpdate",
    "UserRead",
    "get_user_db",
]
