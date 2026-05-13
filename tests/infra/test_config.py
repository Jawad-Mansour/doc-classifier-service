from app.core.config import settings


def test_config_exposes_required_infra_settings():
    required = [
        "APP_NAME",
        "APP_VERSION",
        "DEBUG",
        "DATABASE_URL",
        "DATABASE_SYNC_URL",
        "REDIS_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "QUEUE_NAME",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET",
        "SFTP_HOST",
        "SFTP_PORT",
        "SFTP_USERNAME",
        "SFTP_PASSWORD",
        "SFTP_REMOTE_FOLDER",
        "SFTP_PROCESSED_FOLDER",
        "VAULT_URL",
        "VAULT_TOKEN",
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
    ]

    for name in required:
        assert hasattr(settings, name)
