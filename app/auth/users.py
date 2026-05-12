"""FastAPI Users authentication model and adapters."""

import uuid
from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, Authenticator, BearerTransport
from fastapi_users.db import BaseUserDatabase
from fastapi_users.manager import UUIDIDMixin
from fastapi_users.password import PasswordHelper
from fastapi_users.router import get_auth_router, get_register_router
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate

from app.auth.jwt import get_jwt_strategy
from app.core.security import security_settings


class User(BaseUser):
    role: str | None = None


class UserCreate(BaseUserCreate):
    pass


class UserUpdate(BaseUserUpdate):
    pass


class UserRead(User):
    pass


class UserDB(User, BaseModel):
    """User model used by the auth manager and persistence layer."""

    hashed_password: str


class UserRepository(Protocol):
    async def get(self, id: uuid.UUID) -> Optional[UserDB]:
        ...

    async def get_by_email(self, email: str) -> Optional[UserDB]:
        ...

    async def create(self, user: UserDB) -> UserDB:
        ...

    async def update(self, user: UserDB) -> UserDB:
        ...

    async def delete(self, user: UserDB) -> None:
        ...


class InMemoryUserRepository:
    """Temporary in-memory user store for auth plumbing."""

    def __init__(self) -> None:
        self._users: Dict[uuid.UUID, UserDB] = {}

    async def get(self, id: uuid.UUID) -> Optional[UserDB]:
        return self._users.get(id)

    async def get_by_email(self, email: str) -> Optional[UserDB]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def create(self, user: UserDB) -> UserDB:
        if user.id in self._users:
            raise ValueError("User already exists")
        self._users[user.id] = user
        return user

    async def update(self, user: UserDB) -> UserDB:
        self._users[user.id] = user
        return user

    async def delete(self, user: UserDB) -> None:
        self._users.pop(user.id, None)


class InMemoryUserDatabase(BaseUserDatabase[UserDB, uuid.UUID]):
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def get(self, id: uuid.UUID) -> Optional[UserDB]:
        return await self.repository.get(id)

    async def get_by_email(self, email: str) -> Optional[UserDB]:
        return await self.repository.get_by_email(email)

    async def get_by_oauth_account(self, oauth: str, account_id: str) -> Optional[UserDB]:
        return None

    async def create(self, create_dict: dict[str, Any]) -> UserDB:
        if "id" not in create_dict:
            create_dict["id"] = uuid.uuid4()
        user = UserDB(**create_dict)
        return await self.repository.create(user)

    async def update(self, user: UserDB, update_dict: dict[str, Any]) -> UserDB:
        updated_user = user.model_copy(update=update_dict)
        return await self.repository.update(updated_user)

    async def delete(self, user: UserDB) -> None:
        await self.repository.delete(user)

    async def add_oauth_account(self, user: UserDB, create_dict: dict[str, Any]) -> UserDB:
        return user

    async def update_oauth_account(self, user: UserDB, oauth_account: Any, update_dict: dict[str, Any]) -> UserDB:
        return user


class UserManager(UUIDIDMixin, BaseUserManager[UserDB, uuid.UUID]):
    reset_password_token_secret = security_settings.SECRET_KEY
    verification_token_secret = security_settings.SECRET_KEY

    async def on_after_register(self, user: UserDB, request: Any | None = None) -> None:
        """Hook executed after user registration."""
        return None


user_repository = InMemoryUserRepository()
user_db = InMemoryUserDatabase(user_repository)
password_helper = PasswordHelper()


async def get_user_manager() -> UserManager:
    yield UserManager(user_db, password_helper)


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
]
