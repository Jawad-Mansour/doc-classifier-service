from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.db.models import User
from app.domain.user import UserDomain
from app.exceptions import LastAdminError, UserNotFound
from app.repositories import user_repository
from app.services import audit_service, cache_service
from app.services.role_service import RoleService


pwd_helper = PasswordHelper()


async def register_user(session: AsyncSession, email: str, plain: str) -> UserDomain:
    hashed = pwd_helper.hash(plain)
    user = await user_repository.create(session, email, hashed, UserRole.AUDITOR)
    await session.commit()
    return UserDomain.model_validate(user)


async def seed_demo_user(session: AsyncSession, email: str, plain: str, role: str) -> User:
    """Create/update a demo auth user in Postgres and align its Casbin role."""
    user = await user_repository.get_by_email(session, email)
    if user is None:
        user = await user_repository.create(
            session,
            email,
            pwd_helper.hash(plain),
            role,
            is_verified=True,
        )
    else:
        user.role = role
        user.is_active = True
        user.is_verified = True
        await session.flush()
        await session.refresh(user)

    await RoleService.assign_role(str(user.id), role)
    await cache_service.invalidate_auth_user(str(user.id))
    return user


async def toggle_role(
    session: AsyncSession,
    user_id: int,
    new_role: str,
    actor: str,
) -> UserDomain:
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise UserNotFound
    if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
        admin_count = await user_repository.count_by_role(session, UserRole.ADMIN)
        if admin_count <= 1:
            raise LastAdminError
    updated = await user_repository.update_role(session, user_id, new_role)
    if updated is None:
        raise UserNotFound
    await RoleService.assign_role(str(updated.id), new_role)
    await audit_service.log_event(session, actor, "role_change", f"user:{user_id}")
    await session.commit()
    await cache_service.invalidate_auth_user(str(updated.id))
    return UserDomain.model_validate(updated)
