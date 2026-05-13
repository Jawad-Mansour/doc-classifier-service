from minio import Minio

from app.core.config import settings


minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,
)

BUCKET_NAME = settings.MINIO_BUCKET


def ensure_bucket_exists():
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)


def upload_file(
    local_path: str,
    object_name: str
):
    ensure_bucket_exists()

    minio_client.fput_object(
        BUCKET_NAME,
        object_name,
        local_path,
    )

    return object_name