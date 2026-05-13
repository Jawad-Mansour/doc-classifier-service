import asyncio
import inspect
import atexit
from collections.abc import Callable
from typing import Any

from app.classifier.inference.overlays import create_prediction_overlay
from app.classifier.inference.predictor import DocumentClassifierPredictor
from app.classifier.inference.types import PredictionResult
from app.core.constants import BatchStatus
from app.infra.blob.minio_client import MinioBlobClient


REQUIRED_PAYLOAD_KEYS = {
    "job_id",
    "batch_id",
    "document_id",
    "blob_bucket",
    "blob_path",
    "original_filename",
    "request_id",
}


_ASYNC_RUNNER: asyncio.Runner | None = None


def _get_async_runner() -> asyncio.Runner:
    global _ASYNC_RUNNER
    if _ASYNC_RUNNER is None:
        _ASYNC_RUNNER = asyncio.Runner()
    return _ASYNC_RUNNER


def _close_async_runner() -> None:
    global _ASYNC_RUNNER
    if _ASYNC_RUNNER is not None:
        _ASYNC_RUNNER.close()
        _ASYNC_RUNNER = None


atexit.register(_close_async_runner)


def validate_payload(payload: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_PAYLOAD_KEYS - payload.keys())
    if missing:
        raise ValueError(f"Missing required inference payload keys: {', '.join(missing)}")


def _top5_to_dicts(prediction: PredictionResult) -> list[dict[str, Any]]:
    return [item.model_dump() for item in prediction.top5]


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _persist_prediction(
    *,
    prediction_service: Any,
    session: Any,
    payload: dict[str, Any],
    prediction: PredictionResult,
    overlay_bucket: str,
    overlay_path: str,
) -> Any:
    return await _maybe_await(
        prediction_service.create_prediction(
            session,
            job_id=str(payload["job_id"]),
            batch_id=int(payload["batch_id"]),
            document_id=int(payload["document_id"]),
            label_id=prediction.label_id,
            label=prediction.label,
            confidence=prediction.confidence,
            top5=_top5_to_dicts(prediction),
            all_probs=prediction.all_probs,
            model_sha256=prediction.model_sha256,
            overlay_bucket=overlay_bucket,
            overlay_path=overlay_path,
            request_id=str(payload["request_id"]),
        )
    )


async def _update_batch_status(
    *,
    batch_service: Any | None,
    session: Any,
    batch_id: int,
    status: str,
) -> None:
    if batch_service is None:
        return
    await _maybe_await(batch_service.update_status(session, batch_id, status))


async def _classify_document_job_async(
    payload: dict[str, Any],
    *,
    blob_client: Any,
    predictor: DocumentClassifierPredictor,
    prediction_service: Any,
    batch_service: Any | None,
    session: Any | None,
    session_factory: Callable[[], Any] | None,
) -> dict[str, Any]:
    validate_payload(payload)

    blob_bucket = str(payload["blob_bucket"])
    blob_path = str(payload["blob_path"])
    batch_id = int(payload["batch_id"])
    document_id = int(payload["document_id"])
    overlay_bucket = blob_bucket
    overlay_path = f"overlays/batch_{batch_id}/{document_id}_overlay.png"

    if session is None:
        if session_factory is None:
            from app.db.session import AsyncSessionLocal

            session_factory = AsyncSessionLocal

        async with session_factory() as managed_session:
            return await _classify_document_job_async(
                payload,
                blob_client=blob_client,
                predictor=predictor,
                prediction_service=prediction_service,
                batch_service=batch_service,
                session=managed_session,
                session_factory=None,
            )

    active_session = session
    try:
        await _update_batch_status(
            batch_service=batch_service,
            session=active_session,
            batch_id=batch_id,
            status=BatchStatus.PROCESSING,
        )

        image_bytes = blob_client.download_bytes(blob_bucket, blob_path)
        prediction = predictor.predict_bytes(image_bytes)
        overlay_bytes = create_prediction_overlay(image_bytes, prediction)

        blob_client.upload_bytes(
            overlay_bucket,
            overlay_path,
            overlay_bytes,
            content_type="image/png",
        )

        await _persist_prediction(
            prediction_service=prediction_service,
            session=active_session,
            payload=payload,
            prediction=prediction,
            overlay_bucket=overlay_bucket,
            overlay_path=overlay_path,
        )
        await _update_batch_status(
            batch_service=batch_service,
            session=active_session,
            batch_id=batch_id,
            status=BatchStatus.DONE,
        )
    except Exception:
        rollback = getattr(active_session, "rollback", None)
        if rollback is not None:
            await _maybe_await(rollback())
        await _update_batch_status(
            batch_service=batch_service,
            session=active_session,
            batch_id=batch_id,
            status=BatchStatus.FAILED,
        )
        raise

    return {
        "status": "success",
        "job_id": str(payload["job_id"]),
        "batch_id": batch_id,
        "document_id": document_id,
        "label_id": prediction.label_id,
        "label": prediction.label,
        "confidence": prediction.confidence,
        "overlay_bucket": overlay_bucket,
        "overlay_path": overlay_path,
        "model_sha256": prediction.model_sha256,
    }


def classify_document_job(
    payload: dict[str, Any],
    *,
    blob_client: Any | None = None,
    predictor: DocumentClassifierPredictor | None = None,
    prediction_service: Any | None = None,
    batch_service: Any | None = None,
    session: Any | None = None,
    session_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    if blob_client is None:
        blob_client = MinioBlobClient()
    if predictor is None:
        predictor = DocumentClassifierPredictor()
    if prediction_service is None:
        from app.services import prediction_service as default_prediction_service

        prediction_service = default_prediction_service
    if batch_service is None and session is None:
        from app.services import batch_service as default_batch_service

        batch_service = default_batch_service

    return _get_async_runner().run(
        _classify_document_job_async(
            payload,
            blob_client=blob_client,
            predictor=predictor,
            prediction_service=prediction_service,
            batch_service=batch_service,
            session=session,
            session_factory=session_factory,
        )
    )
