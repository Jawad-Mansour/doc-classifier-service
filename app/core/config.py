import os

from sqlalchemy.engine import URL, make_url


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _build_database_url(env_name: str, drivername: str) -> str:
    configured = os.getenv(env_name)
    if configured:
        return configured

    username = os.getenv("DATABASE_USER", "postgres")
    host = os.getenv("DATABASE_HOST", "localhost")
    port = int(os.getenv("DATABASE_PORT", "5432"))
    database = os.getenv("DATABASE_NAME", "doc_classifier")
    credential = os.getenv("DATABASE_PASSWORD") or None
    return URL.create(
        drivername=drivername,
        username=username,
        password=credential,
        host=host,
        port=port,
        database=database,
    ).render_as_string(hide_password=False)


class Settings:
    # App
    ENV = os.getenv("ENV", "development")
    APP_NAME = os.getenv("APP_NAME", "Document Classifier Service")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    # Local defaults use localhost.
    # Docker Compose should override these with service hostnames like postgres.
    DATABASE_URL = _build_database_url("DATABASE_URL", "postgresql+asyncpg")

    DATABASE_SYNC_URL = _build_database_url("DATABASE_SYNC_URL", "postgresql+psycopg2")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")

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
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")

    # SFTP
    SFTP_HOST = os.getenv("SFTP_HOST", "localhost")
    SFTP_PORT = int(os.getenv("SFTP_PORT", "2222"))
    SFTP_USERNAME = os.getenv("SFTP_USERNAME", "test")
    SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "")
    SFTP_REMOTE_FOLDER = os.getenv("SFTP_REMOTE_FOLDER", "/upload")
    SFTP_PROCESSED_FOLDER = os.getenv("SFTP_PROCESSED_FOLDER", "/processed")
    SFTP_POLL_INTERVAL_SECONDS = int(os.getenv("SFTP_POLL_INTERVAL_SECONDS", "5"))

    # Vault
    VAULT_URL = os.getenv("VAULT_URL", "http://localhost:8200")
    VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
    REQUIRE_VAULT = _env_bool("REQUIRE_VAULT", False)
    VAULT_SECRET_BASE_PATH = os.getenv("VAULT_SECRET_BASE_PATH", "secret/data/doc-classifier")

    # Auth / JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )

    # Local/demo auth seed users. Startup only uses these when DEBUG and SEED_DEMO_USERS are true.
    SEED_DEMO_USERS = _env_bool("SEED_DEMO_USERS", False)
    DEMO_ADMIN_EMAIL = os.getenv("DEMO_ADMIN_EMAIL", "admin@example.com")
    DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "")
    DEMO_REVIEWER_EMAIL = os.getenv("DEMO_REVIEWER_EMAIL", "reviewer@example.com")
    DEMO_REVIEWER_PASSWORD = os.getenv("DEMO_REVIEWER_PASSWORD", "")
    DEMO_AUDITOR_EMAIL = os.getenv("DEMO_AUDITOR_EMAIL", "auditor@example.com")
    DEMO_AUDITOR_PASSWORD = os.getenv("DEMO_AUDITOR_PASSWORD", "")

    def set_database_password(self, password: str) -> None:
        self.DATABASE_PASSWORD = password
        self.DATABASE_URL = _set_url_password(self.DATABASE_URL, password)
        self.DATABASE_SYNC_URL = _set_url_password(self.DATABASE_SYNC_URL, password)


def _set_url_password(url: str, password: str) -> str:
    parsed = make_url(url)
    return parsed.set(password=password).render_as_string(hide_password=False)


settings = Settings()
