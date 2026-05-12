from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CLASS_NAMES, CONFIDENCE_THRESHOLD
from app.domain.prediction import PredictionDomain
from app.exceptions import PredictionNotFound, UnauthorizedRelabel
from app.repositories import prediction_repository
from app.services import audit_service, cache_service


async def create_prediction(
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
) -> PredictionDomain:
    prediction = await prediction_repository.create(
        session,
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
        request_id=request_id,
    )
    await audit_service.log_event(session, "system", "prediction_created", f"document:{document_id}")
    await session.commit()
    await cache_service.invalidate_predictions()
    return PredictionDomain.model_validate(prediction)


async def list_predictions(session: AsyncSession, batch_id: int) -> list[PredictionDomain]:
    rows = await prediction_repository.list_by_batch_id(session, batch_id)
    return [PredictionDomain.model_validate(r) for r in rows]


async def get_recent(session: AsyncSession, limit: int = 20) -> list[PredictionDomain]:
    rows = await prediction_repository.get_recent(session, limit)
    return [PredictionDomain.model_validate(r) for r in rows]


async def relabel(
    session: AsyncSession,
    prediction_id: int,
    new_label: str,
    reviewer: str,
) -> PredictionDomain:
    prediction = await prediction_repository.get_by_id(session, prediction_id)
    if prediction is None:
        raise PredictionNotFound
    if prediction.confidence >= CONFIDENCE_THRESHOLD:
        raise UnauthorizedRelabel
    new_label_id = CLASS_NAMES.index(new_label)
    updated = await prediction_repository.update_label(
        session, prediction_id, new_label_id, new_label, reviewer
    )
    await audit_service.log_event(session, reviewer, "relabel", f"prediction:{prediction_id}")
    await session.commit()
    await cache_service.invalidate_predictions()
    return PredictionDomain.model_validate(updated)
