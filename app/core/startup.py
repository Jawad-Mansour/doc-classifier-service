from app.infra.blob.minio_client import ensure_bucket_exists
from app.infra.logging.logger import get_logger


logger = get_logger(__name__)


def startup_checks():
    logger.info("Running startup checks...")

    ensure_bucket_exists()

    logger.info("MinIO bucket is ready")
    logger.info("Startup checks completed")