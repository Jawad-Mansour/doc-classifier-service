import logging

from fastapi_cache import FastAPICache

logger = logging.getLogger(__name__)

# Namespace constants — Ali must use these same strings in his @cache() key builders
# so that our invalidation targets the correct Redis keys.
BATCH_NAMESPACE = "batch"
USER_NAMESPACE = "user"
PREDICTIONS_RECENT_NAMESPACE = "predictions:recent"


async def invalidate_batch(batch_id: int) -> None:
    try:
        await FastAPICache.clear(namespace=f"{BATCH_NAMESPACE}:{batch_id}")
    except Exception:
        logger.warning("cache invalidation skipped for batch:%s", batch_id)


async def invalidate_user(user_id: int) -> None:
    try:
        await FastAPICache.clear(namespace=f"{USER_NAMESPACE}:{user_id}")
    except Exception:
        logger.warning("cache invalidation skipped for user:%s", user_id)


async def invalidate_predictions() -> None:
    try:
        await FastAPICache.clear(namespace=PREDICTIONS_RECENT_NAMESPACE)
    except Exception:
        logger.warning("cache invalidation skipped for predictions:recent")
