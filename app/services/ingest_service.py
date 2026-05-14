from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.core.constants import BatchStatus
from app.infra.blob.minio_client import blob_client as default_blob_client
from app.infra.queue.rq_client import enqueue_inference_job


SUPPORTED_UPLOAD_EXTENSIONS = (".tif", ".tiff", ".png", ".jpg", ".jpeg")


def is_supported_upload(filename: str) -> bool:
    return filename.lower().endswith(SUPPORTED_UPLOAD_EXTENSIONS)


def safe_filename(filename: str) -> str:
    return PurePosixPath(filename).name


def infer_content_type(filename: str, content_type: str | None = None) -> str:
    if content_type:
        return content_type

    lower = filename.lower()
    if lower.endswith((".tif", ".tiff")):
        return "image/tiff"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "application/octet-stream"


def _object_id(value: Any) -> int:
    if isinstance(value, dict):
        return int(value["id"])
    return int(value.id)


async def enqueue_uploaded_document(
    session: Any,
    *,
    batch_service: Any,
    filename: str,
    file_bytes: bytes,
    content_type: str | None = None,
    blob_client: Any = default_blob_client,
    queue_enqueue: Any = enqueue_inference_job,
    request_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    original_filename = safe_filename(filename)
    if not is_supported_upload(original_filename):
        raise ValueError(f"Unsupported file extension: {filename}")

    request_id = request_id or str(uuid4())
    job_id = job_id or str(uuid4())

    batch = await batch_service.create_batch(session, request_id)
    batch_id = _object_id(batch)
    blob_bucket = settings.MINIO_BUCKET
    blob_path = f"raw/batch_{batch_id}/{original_filename}"

    document = await batch_service.add_document(
        session,
        batch_id=batch_id,
        filename=original_filename,
        blob_bucket=blob_bucket,
        blob_path=blob_path,
    )
    document_id = _object_id(document)

    blob_client.upload_bytes(
        blob_bucket,
        blob_path,
        file_bytes,
        content_type=infer_content_type(original_filename, content_type),
    )

    payload = {
        "job_id": job_id,
        "batch_id": batch_id,
        "document_id": document_id,
        "blob_bucket": blob_bucket,
        "blob_path": blob_path,
        "original_filename": original_filename,
        "request_id": request_id,
    }
    queue_job_id = queue_enqueue(payload)
    await batch_service.update_status(session, batch_id, BatchStatus.PROCESSING)

    return {
        "status": "queued",
        "request_id": request_id,
        "job_id": job_id,
        "queue_job_id": queue_job_id,
        "batch_id": batch_id,
        "document_id": document_id,
        "blob_bucket": blob_bucket,
        "blob_path": blob_path,
        "original_filename": original_filename,
    }
