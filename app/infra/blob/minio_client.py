from io import BytesIO

from minio import Minio

from app.core.config import settings


class MinioBlobClient:
    def __init__(self, client: Minio | None = None) -> None:
        self.client = client or Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )

    def ensure_bucket(self, bucket: str) -> None:
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def download_bytes(self, bucket: str, path: str) -> bytes:
        response = self.client.get_object(bucket, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def upload_bytes(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.ensure_bucket(bucket)
        self.client.put_object(
            bucket,
            path,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )


blob_client = MinioBlobClient()


def ensure_bucket(bucket: str) -> None:
    blob_client.ensure_bucket(bucket)


def download_bytes(bucket: str, path: str) -> bytes:
    return blob_client.download_bytes(bucket, path)


def upload_bytes(
    bucket: str,
    path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    blob_client.upload_bytes(bucket, path, data, content_type=content_type)
