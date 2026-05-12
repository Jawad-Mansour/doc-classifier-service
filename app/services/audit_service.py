from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import AuditLogDomain
from app.repositories import audit_repository


async def log_event(session: AsyncSession, actor: str, action: str, target: str) -> None:
    await audit_repository.create(session, actor, action, target)


async def list_logs(session: AsyncSession) -> list[AuditLogDomain]:
    rows = await audit_repository.list_all(session)
    return [AuditLogDomain.model_validate(r) for r in rows]


async def list_logs_by_actor(session: AsyncSession, actor: str) -> list[AuditLogDomain]:
    rows = await audit_repository.list_by_actor(session, actor)
    return [AuditLogDomain.model_validate(r) for r in rows]
