from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.batch import BatchDomain
from app.domain.document import DocumentDomain
from app.exceptions import BatchNotFound
from app.repositories import batch_repository, document_repository
from app.services import audit_service, cache_service


async def create_batch(session: AsyncSession, request_id: str) -> BatchDomain:
    batch = await batch_repository.create(session, request_id)
    await session.commit()
    return BatchDomain.model_validate(batch)


async def add_document(
    session: AsyncSession,
    batch_id: int,
    filename: str,
    blob_bucket: str,
    blob_path: str,
) -> DocumentDomain:
    doc = await document_repository.create(session, batch_id, filename, blob_bucket, blob_path)
    await session.commit()
    return DocumentDomain.model_validate(doc)


async def get_batch(session: AsyncSession, batch_id: int) -> BatchDomain:
    batch = await batch_repository.get_by_id(session, batch_id)
    if batch is None:
        raise BatchNotFound
    return BatchDomain.model_validate(batch)


async def list_batches(session: AsyncSession) -> list[BatchDomain]:
    rows = await batch_repository.list_all(session)
    return [BatchDomain.model_validate(r) for r in rows]


async def update_status(session: AsyncSession, batch_id: int, status: str) -> BatchDomain:
    batch = await batch_repository.update_status(session, batch_id, status)
    if batch is None:
        raise BatchNotFound
    await audit_service.log_event(session, "system", "status_change", f"batch:{batch_id}")
    await session.commit()
    await cache_service.invalidate_batch(batch_id)
    return BatchDomain.model_validate(batch)
