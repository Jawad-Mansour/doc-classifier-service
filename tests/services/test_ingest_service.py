from types import SimpleNamespace

import pytest

from app.services import ingest_service


class FakeBlobClient:
    def __init__(self) -> None:
        self.uploads: list[dict[str, object]] = []

    def upload_bytes(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.uploads.append(
            {
                "bucket": bucket,
                "path": path,
                "data": data,
                "content_type": content_type,
            }
        )


class FakeBatchService:
    def __init__(self) -> None:
        self.status_updates: list[tuple[int, str]] = []

    async def create_batch(self, session: object, request_id: str) -> object:
        return SimpleNamespace(id=12)

    async def add_document(
        self,
        session: object,
        batch_id: int,
        filename: str,
        blob_bucket: str,
        blob_path: str,
    ) -> object:
        return SimpleNamespace(id=44)

    async def update_status(self, session: object, batch_id: int, status: str) -> object:
        self.status_updates.append((batch_id, status))
        return SimpleNamespace(id=batch_id, status=status)


@pytest.mark.asyncio
async def test_enqueue_uploaded_document_uploads_and_enqueues():
    blob_client = FakeBlobClient()
    batch_service = FakeBatchService()
    queued_payloads: list[dict[str, object]] = []

    def queue_enqueue(payload: dict[str, object]) -> str:
        queued_payloads.append(payload)
        return "rq-job-1"

    result = await ingest_service.enqueue_uploaded_document(
        object(),
        batch_service=batch_service,
        filename="sample.png",
        file_bytes=b"png-bytes",
        content_type="image/png",
        blob_client=blob_client,
        queue_enqueue=queue_enqueue,
        request_id="request-1",
        job_id="job-1",
    )

    assert blob_client.uploads == [
        {
            "bucket": "documents",
            "path": "raw/batch_12/sample.png",
            "data": b"png-bytes",
            "content_type": "image/png",
        }
    ]
    assert queued_payloads == [
        {
            "job_id": "job-1",
            "batch_id": 12,
            "document_id": 44,
            "blob_bucket": "documents",
            "blob_path": "raw/batch_12/sample.png",
            "original_filename": "sample.png",
            "request_id": "request-1",
        }
    ]
    assert result["status"] == "queued"
    assert result["batch_id"] == 12
    assert batch_service.status_updates == [(12, "processing")]


@pytest.mark.asyncio
async def test_enqueue_uploaded_document_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file extension"):
        await ingest_service.enqueue_uploaded_document(
            object(),
            batch_service=FakeBatchService(),
            filename="sample.pdf",
            file_bytes=b"pdf-bytes",
        )
