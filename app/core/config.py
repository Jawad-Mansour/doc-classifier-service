import os


class Settings:
    # App
    ENV = os.getenv("ENV", "development")
    APP_NAME = os.getenv("APP_NAME", "Document Classifier Service")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    # Local defaults use localhost.
    # Docker Compose should override these with service hostnames like postgres.
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/doc_classifier",
    )

    DATABASE_SYNC_URL = os.getenv(
        "DATABASE_SYNC_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/doc_classifier",
    )

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL = os.getenv(
        "REDIS_URL",
        f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
    )
    QUEUE_NAME = os.getenv("QUEUE_NAME", "default")

    # MinIO
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")

    # SFTP
    SFTP_HOST = os.getenv("SFTP_HOST", "localhost")
    SFTP_PORT = int(os.getenv("SFTP_PORT", "2222"))
    SFTP_USERNAME = os.getenv("SFTP_USERNAME", "test")
    SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "test")
    SFTP_REMOTE_FOLDER = os.getenv("SFTP_REMOTE_FOLDER", "/upload")
    SFTP_PROCESSED_FOLDER = os.getenv("SFTP_PROCESSED_FOLDER", "/processed")
    SFTP_POLL_INTERVAL_SECONDS = int(os.getenv("SFTP_POLL_INTERVAL_SECONDS", "5"))

    # Vault
    VAULT_URL = os.getenv("VAULT_URL", "http://localhost:8200")
    VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root")

    # Auth / JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )


settings = Settings()
