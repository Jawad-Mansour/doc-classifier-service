from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document


async def create(
    session: AsyncSession,
    batch_id: int,
    filename: str,
    blob_bucket: str,
    blob_path: str,
) -> Document:
    doc = Document(
        batch_id=batch_id,
        filename=filename,
        blob_bucket=blob_bucket,
        blob_path=blob_path,
    )
    session.add(doc)
    await session.flush()
    await session.refresh(doc)
    return doc


async def get_by_id(session: AsyncSession, document_id: int) -> Document | None:
    return await session.get(Document, document_id)


async def list_by_batch_id(session: AsyncSession, batch_id: int) -> list[Document]:
    result = await session.execute(
        select(Document)
        .where(Document.batch_id == batch_id)
        .order_by(Document.created_at)
    )
    return list(result.scalars().all())
