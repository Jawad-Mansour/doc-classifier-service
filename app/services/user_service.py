from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.core.security import hash_pwd
from app.domain.user import UserDomain
from app.exceptions import LastAdminError, UserNotFound
from app.repositories import user_repository
from app.services import audit_service, cache_service


async def register_user(session: AsyncSession, email: str, plain: str) -> UserDomain:
    hashed = hash_pwd(plain)
    user = await user_repository.create(session, email, hashed, UserRole.AUDITOR)
    await session.commit()
    return UserDomain.model_validate(user)


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
    await audit_service.log_event(session, actor, "role_change", f"user:{user_id}")
    await session.commit()
    await cache_service.invalidate_user(user_id)
    return UserDomain.model_validate(updated)


