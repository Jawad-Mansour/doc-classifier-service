import asyncio
from typing import Any

from app.core.config import settings
from app.infra.blob.minio_client import blob_client as default_blob_client
from app.infra.queue.rq_client import enqueue_inference_job
from app.infra.sftp.client import SFTPClient, is_valid_tiff
from app.services.ingest_service import enqueue_uploaded_document


PROCESSED_FILES: set[str] = set()


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

    image_bytes = sftp_client.download_bytes(filename)
    result = await enqueue_uploaded_document(
        session,
        batch_service=batch_service,
        filename=filename,
        file_bytes=image_bytes,
        content_type="image/tiff",
        blob_client=blob_client,
        queue_enqueue=queue_enqueue,
        request_id=request_id,
        job_id=job_id,
    )

    if hasattr(sftp_client, "move_to_processed"):
        sftp_client.move_to_processed(filename)

    print(
        "Queued inference job "
        f"request_id={result['request_id']} job_id={result['job_id']} queue_job_id={result['queue_job_id']} "
        f"batch_id={result['batch_id']} document_id={result['document_id']} filename={result['original_filename']}"
    )

    return result


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


async def _run_forever(poll_interval: int) -> None:
    while True:
        try:
            await _run_once_with_runtime_clients()
        except Exception as exc:
            print(f"SFTP ingest error: {exc}")
        await asyncio.sleep(poll_interval)


def run(poll_interval_seconds: int | None = None) -> None:
    poll_interval = poll_interval_seconds or settings.SFTP_POLL_INTERVAL_SECONDS
    print(f"SFTP ingest worker started poll_interval_seconds={poll_interval}")

    asyncio.run(_run_forever(poll_interval))


if __name__ == "__main__":
    run()
