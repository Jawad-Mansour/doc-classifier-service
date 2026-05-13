import os


class Settings:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")

    SFTP_HOST = os.getenv("SFTP_HOST", "localhost")
    SFTP_PORT = int(os.getenv("SFTP_PORT", 2222))
    SFTP_USERNAME = os.getenv("SFTP_USERNAME", "test")
    SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "test")
    SFTP_REMOTE_FOLDER = os.getenv(
        "SFTP_REMOTE_FOLDER",
        "/upload"
    )

    VAULT_URL = os.getenv(
        "VAULT_URL",
        "http://localhost:8200"
    )

    VAULT_TOKEN = os.getenv(
        "VAULT_TOKEN",
        "root"
    )


settings = Settings()