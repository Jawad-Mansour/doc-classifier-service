from unittest.mock import AsyncMock, patch

import pytest

from app.services import cache_service


@pytest.mark.asyncio
async def test_invalidate_batch_falls_back_to_direct_redis_clear():
    fake_redis = AsyncMock()
    fake_redis.scan.side_effect = [(0, [b"fastapi-cache:batches:key1"]), (0, [b"fastapi-cache:batch:7:key2"])]

    with (
        patch("app.services.cache_service.FastAPICache.clear", new_callable=AsyncMock, side_effect=RuntimeError("not init")),
        patch("app.services.cache_service.aioredis.from_url", return_value=fake_redis),
    ):
        await cache_service.invalidate_batch(7)

    assert fake_redis.delete.await_count == 2
    assert fake_redis.aclose.await_count == 2


@pytest.mark.asyncio
async def test_invalidate_predictions_falls_back_to_direct_redis_clear():
    fake_redis = AsyncMock()
    fake_redis.scan.return_value = (0, [b"fastapi-cache:predictions:recent:key1"])

    with (
        patch("app.services.cache_service.FastAPICache.clear", new_callable=AsyncMock, side_effect=RuntimeError("not init")),
        patch("app.services.cache_service.aioredis.from_url", return_value=fake_redis),
    ):
        await cache_service.invalidate_predictions()

    fake_redis.delete.assert_awaited_once()
