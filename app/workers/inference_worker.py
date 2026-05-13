import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from app.classifier.inference.overlays import create_prediction_overlay
from app.classifier.inference.predictor import DocumentClassifierPredictor
from app.classifier.inference.types import PredictionResult
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


async def _classify_document_job_async(
    payload: dict[str, Any],
    *,
    blob_client: Any,
    predictor: DocumentClassifierPredictor,
    prediction_service: Any,
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

    image_bytes = blob_client.download_bytes(blob_bucket, blob_path)
    prediction = predictor.predict_bytes(image_bytes)
    overlay_bytes = create_prediction_overlay(image_bytes, prediction)

    blob_client.upload_bytes(
        overlay_bucket,
        overlay_path,
        overlay_bytes,
        content_type="image/png",
    )

    if session is not None:
        await _persist_prediction(
            prediction_service=prediction_service,
            session=session,
            payload=payload,
            prediction=prediction,
            overlay_bucket=overlay_bucket,
            overlay_path=overlay_path,
        )
    else:
        if session_factory is None:
            from app.db.session import AsyncSessionLocal

            session_factory = AsyncSessionLocal

        async with session_factory() as managed_session:
            await _persist_prediction(
                prediction_service=prediction_service,
                session=managed_session,
                payload=payload,
                prediction=prediction,
                overlay_bucket=overlay_bucket,
                overlay_path=overlay_path,
            )

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

    return asyncio.run(
        _classify_document_job_async(
            payload,
            blob_client=blob_client,
            predictor=predictor,
            prediction_service=prediction_service,
            session=session,
            session_factory=session_factory,
        )
    )
