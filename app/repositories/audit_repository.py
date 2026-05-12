from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


async def create(session: AsyncSession, actor: str, action: str, target: str) -> AuditLog:
    log = AuditLog(actor=actor, action=action, target=target)
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log


async def list_all(session: AsyncSession) -> list[AuditLog]:
    result = await session.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()))
    return list(result.scalars().all())


async def list_by_actor(session: AsyncSession, actor: str) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.actor == actor)
        .order_by(AuditLog.timestamp.desc())
    )
    return list(result.scalars().all())
