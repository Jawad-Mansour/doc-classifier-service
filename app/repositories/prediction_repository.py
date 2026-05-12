from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Prediction


async def create(
    session: AsyncSession,
    job_id: str,
    batch_id: int,
    document_id: int,
    label_id: int,
    label: str,
    confidence: float,
    top5: list,
    all_probs: dict,
    model_sha256: str,
    overlay_bucket: str,
    overlay_path: str,
    request_id: str,
) -> Prediction:
    prediction = Prediction(
        job_id=job_id,
        batch_id=batch_id,
        document_id=document_id,
        label_id=label_id,
        label=label,
        confidence=confidence,
        top5=top5,
        all_probs=all_probs,
        model_sha256=model_sha256,
        overlay_bucket=overlay_bucket,
        overlay_path=overlay_path,
        relabeled_by=None,
        request_id=request_id,
    )
    session.add(prediction)
    await session.flush()
    await session.refresh(prediction)
    return prediction


async def get_by_id(session: AsyncSession, prediction_id: int) -> Prediction | None:
    return await session.get(Prediction, prediction_id)


async def list_by_batch_id(session: AsyncSession, batch_id: int) -> list[Prediction]:
    result = await session.execute(
        select(Prediction)
        .where(Prediction.batch_id == batch_id)
        .order_by(Prediction.created_at)
    )
    return list(result.scalars().all())


async def get_recent(session: AsyncSession, limit: int) -> list[Prediction]:
    result = await session.execute(
        select(Prediction).order_by(Prediction.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def update_label(
    session: AsyncSession,
    prediction_id: int,
    new_label_id: int,
    new_label: str,
    relabeled_by: str,
) -> Prediction | None:
    prediction = await session.get(Prediction, prediction_id)
    if prediction is None:
        return None
    prediction.label_id = new_label_id
    prediction.label = new_label
    prediction.relabeled_by = relabeled_by
    await session.flush()
    await session.refresh(prediction)
    return prediction
