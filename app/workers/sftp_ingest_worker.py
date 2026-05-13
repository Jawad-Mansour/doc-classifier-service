import asyncio
import inspect
import time
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.infra.blob.minio_client import blob_client as default_blob_client
from app.infra.queue.rq_client import enqueue_inference_job
from app.infra.sftp.client import SFTPClient, is_valid_tiff


PROCESSED_FILES: set[str] = set()


def _safe_filename(filename: str) -> str:
    return PurePosixPath(filename).name


def _object_id(value: Any) -> int:
    if isinstance(value, dict):
        return int(value["id"])
    return int(value.id)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def process_sftp_file(
    filename: str,
    *,
    sftp_client: Any,
    session: Any,
    batch_service: Any,
    blob_client: Any = default_blob_client,
    queue_enqueue: Any = enqueue_inference_job,
    request_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    if not is_valid_tiff(filename):
        raise ValueError(f"Unsupported SFTP file extension: {filename}")

    request_id = request_id or str(uuid4())
    job_id = job_id or str(uuid4())
    original_filename = _safe_filename(filename)

    batch = await _maybe_await(batch_service.create_batch(session, request_id))
    batch_id = _object_id(batch)
    blob_bucket = settings.MINIO_BUCKET
    blob_path = f"raw/batch_{batch_id}/{original_filename}"

    document = await _maybe_await(
        batch_service.add_document(
            session,
            batch_id=batch_id,
            filename=original_filename,
            blob_bucket=blob_bucket,
            blob_path=blob_path,
        )
    )
    document_id = _object_id(document)

    image_bytes = sftp_client.download_bytes(filename)
    blob_client.upload_bytes(
        blob_bucket,
        blob_path,
        image_bytes,
        content_type="image/tiff",
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

    if hasattr(sftp_client, "move_to_processed"):
        sftp_client.move_to_processed(filename)

    print(
        "Queued inference job "
        f"request_id={request_id} job_id={job_id} queue_job_id={queue_job_id} "
        f"batch_id={batch_id} document_id={document_id} filename={original_filename}"
    )

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


async def poll_sftp_once(
    *,
    sftp_client: Any,
    session: Any,
    batch_service: Any,
    blob_client: Any = default_blob_client,
    queue_enqueue: Any = enqueue_inference_job,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for filename in sftp_client.list_files():
        if filename in PROCESSED_FILES:
            continue

        if not is_valid_tiff(filename):
            print(f"Skipping unsupported SFTP file: {filename}")
            PROCESSED_FILES.add(filename)
            continue

        result = await process_sftp_file(
            filename,
            sftp_client=sftp_client,
            session=session,
            batch_service=batch_service,
            blob_client=blob_client,
            queue_enqueue=queue_enqueue,
        )
        PROCESSED_FILES.add(filename)
        results.append(result)

    return results


async def _run_once_with_runtime_clients() -> list[dict[str, Any]]:
    from app.db.session import AsyncSessionLocal
    from app.services import batch_service

    with SFTPClient() as sftp_client:
        async with AsyncSessionLocal() as session:
            return await poll_sftp_once(
                sftp_client=sftp_client,
                session=session,
                batch_service=batch_service,
            )


def run(poll_interval_seconds: int | None = None) -> None:
    poll_interval = poll_interval_seconds or settings.SFTP_POLL_INTERVAL_SECONDS
    print(f"SFTP ingest worker started poll_interval_seconds={poll_interval}")

    while True:
        try:
            asyncio.run(_run_once_with_runtime_clients())
        except Exception as exc:
            print(f"SFTP ingest error: {exc}")

        time.sleep(poll_interval)


if __name__ == "__main__":
    run()
