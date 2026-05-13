from types import SimpleNamespace

import pytest

from app.workers.sftp_ingest_worker import process_sftp_file


class FakeSFTPClient:
    def __init__(self) -> None:
        self.downloaded: list[str] = []
        self.moved: list[str] = []

    def download_bytes(self, filename: str) -> bytes:
        self.downloaded.append(filename)
        return b"fake-tiff-bytes"

    def move_to_processed(self, filename: str) -> None:
        self.moved.append(filename)


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
async def test_process_sftp_file_uploads_and_enqueues_payload():
    sftp_client = FakeSFTPClient()
    blob_client = FakeBlobClient()
    queued_payloads: list[dict[str, object]] = []
    batch_service = FakeBatchService()

    def queue_enqueue(payload: dict[str, object]) -> str:
        queued_payloads.append(payload)
        return "rq-job-1"

    result = await process_sftp_file(
        "file1.tiff",
        sftp_client=sftp_client,
        session=object(),
        batch_service=batch_service,
        blob_client=blob_client,
        queue_enqueue=queue_enqueue,
        request_id="request-1",
        job_id="job-1",
    )

    assert sftp_client.downloaded == ["file1.tiff"]
    assert sftp_client.moved == ["file1.tiff"]
    assert blob_client.uploads[0]["bucket"] == "documents"
    assert blob_client.uploads[0]["path"] == "raw/batch_12/file1.tiff"
    assert blob_client.uploads[0]["content_type"] == "image/tiff"
    assert queued_payloads == [
        {
            "job_id": "job-1",
            "batch_id": 12,
            "document_id": 44,
            "blob_bucket": "documents",
            "blob_path": "raw/batch_12/file1.tiff",
            "original_filename": "file1.tiff",
            "request_id": "request-1",
        }
    ]
    assert result["status"] == "queued"
    assert result["queue_job_id"] == "rq-job-1"
    assert batch_service.status_updates == [(12, "processing")]
