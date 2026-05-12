from minio import Minio

minio_client = Minio(
    "localhost:9000",
    access_key="minio",
    secret_key="minio123",
    secure=False
)

BUCKET_NAME = "documents"


def ensure_bucket_exists():
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)


def upload_file(local_path: str, object_name: str):
    ensure_bucket_exists()

    minio_client.fput_object(
        BUCKET_NAME,
        object_name,
        local_path
    )

    return object_name