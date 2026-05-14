import logging
import inspect
from hashlib import md5
from typing import Any

from fastapi_cache import FastAPICache
from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Namespace constants - routers must use these same strings in their @cache() decorators
# so that our invalidation targets the correct Redis keys.
BATCHES_NAMESPACE = "batches"
BATCH_NAMESPACE = "batch"
AUTH_ME_NAMESPACE = "auth:me"
PREDICTIONS_RECENT_NAMESPACE = "predictions:recent"


def batch_namespace(batch_id: int) -> str:
    return f"{BATCH_NAMESPACE}:{batch_id}"


def auth_me_namespace(subject: str | int) -> str:
    return f"{AUTH_ME_NAMESPACE}:{subject}"


def _cache_key(prefix: str, namespace: str, identity: str) -> str:
    key = md5(identity.encode()).hexdigest()
    return f"{prefix}:{namespace}:{key}"


def _cache_prefix() -> str:
    try:
        return FastAPICache.get_prefix()
    except Exception:
        return "fastapi-cache"


def batch_detail_key_builder(
    func: Any,
    namespace: str = "",
    *,
    request: Any = None,
    response: Any = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    del args, response
    kwargs = kwargs or {}
    batch_id = kwargs.get("bid")
    if batch_id is None and request is not None:
        batch_id = request.path_params.get("bid")
    detail_namespace = batch_namespace(int(batch_id)) if batch_id is not None else namespace
    identity = f"{func.__module__}:{func.__name__}:{batch_id}"
    return _cache_key(_cache_prefix(), detail_namespace, identity)


def auth_me_key_builder(
    func: Any,
    namespace: str = "",
    *,
    request: Any = None,
    response: Any = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    del args, request, response
    kwargs = kwargs or {}
    user = kwargs.get("user")
    subject = getattr(user, "id", None)
    auth_namespace = auth_me_namespace(str(subject)) if subject is not None else namespace
    identity = f"{func.__module__}:{func.__name__}:{subject}"
    return _cache_key(_cache_prefix(), auth_namespace, identity)


async def _clear(namespace: str) -> None:
    try:
        await FastAPICache.clear(namespace=namespace)
    except Exception:
        redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=False)
        try:
            pattern = f"{_cache_prefix()}:{namespace}:*"
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await redis.delete(*keys)
                if cursor == 0:
                    break
        finally:
            close = getattr(redis, "aclose", None) or getattr(redis, "close", None)
            if close is not None:
                result = close()
                if inspect.isawaitable(result):
                    await result


async def invalidate_batches() -> None:
    try:
        await _clear(BATCHES_NAMESPACE)
    except Exception:
        logger.warning("cache invalidation skipped for batches")


async def invalidate_batch(batch_id: int) -> None:
    try:
        await _clear(BATCHES_NAMESPACE)
        await _clear(batch_namespace(batch_id))
    except Exception:
        logger.warning("cache invalidation skipped for batch:%s", batch_id)


async def invalidate_auth_user(subject: str | int) -> None:
    try:
        await _clear(auth_me_namespace(subject))
    except Exception:
        logger.warning("cache invalidation skipped for auth user:%s", subject)


async def invalidate_user(user_id: int) -> None:
    await invalidate_auth_user(user_id)


async def invalidate_predictions() -> None:
    try:
        await _clear(PREDICTIONS_RECENT_NAMESPACE)
    except Exception:
        logger.warning("cache invalidation skipped for predictions:recent")


async def invalidate_prediction_write(batch_id: int) -> None:
    await invalidate_predictions()
    await invalidate_batch(batch_id)
