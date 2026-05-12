from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Batch


async def create(session: AsyncSession, request_id: str) -> Batch:
    batch = Batch(request_id=request_id, status="pending")
    session.add(batch)
    await session.flush()
    await session.refresh(batch)
    return batch


async def get_by_id(session: AsyncSession, batch_id: int) -> Batch | None:
    return await session.get(Batch, batch_id)


async def list_all(session: AsyncSession) -> list[Batch]:
    result = await session.execute(select(Batch).order_by(Batch.created_at.desc()))
    return list(result.scalars().all())


async def update_status(session: AsyncSession, batch_id: int, status: str) -> Batch | None:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        return None
    batch.status = status
    await session.flush()
    await session.refresh(batch)
    return batch
