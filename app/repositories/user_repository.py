from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.__table__.c.email == email))
    return result.scalar_one_or_none()


async def count_by_role(session: AsyncSession, role: str) -> int:
    result = await session.execute(
        select(func.count()).select_from(User).where(User.role == role)
    )
    return result.scalar_one()


async def create(
    session: AsyncSession,
    email: str,
    hashed_password: str,
    role: str,
    *,
    is_verified: bool = False,
) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_active=True,
        is_superuser=False,
        is_verified=is_verified,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def update_role(session: AsyncSession, user_id: int, new_role: str) -> User | None:
    user = await session.get(User, user_id)
    if user is None:
        return None
    user.role = new_role
    await session.flush()
    await session.refresh(user)
    return user
