"""
Health check router.

Health and readiness endpoints for local infrastructure and monitoring.
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis
from sqlalchemy import text

from app.api.schemas import HealthResponse
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.infra.blob.minio_client import blob_client
from app.infra.vault import vault_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns service status for Kubernetes probes and monitoring.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Readiness check across required backing services.
    """
    payload = await collect_readiness()
    status_code = 200 if payload["ready"] else 503
    return JSONResponse(status_code=status_code, content=payload)


async def collect_readiness() -> dict[str, object]:
    checks: dict[str, bool] = {
        "database": False,
        "redis": False,
        "minio": False,
    }
    if settings.REQUIRE_VAULT:
        checks["vault"] = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=False)
    try:
        checks["redis"] = bool(await redis.ping())
    except Exception:
        checks["redis"] = False
    finally:
        close = getattr(redis, "aclose", None) or getattr(redis, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result

    try:
        await asyncio.to_thread(blob_client.ensure_bucket, settings.MINIO_BUCKET)
        checks["minio"] = True
    except Exception:
        checks["minio"] = False

    if settings.REQUIRE_VAULT:
        try:
            checks["vault"] = bool(await asyncio.to_thread(vault_client.is_available))
        except Exception:
            checks["vault"] = False

    return {
        "ready": all(checks.values()),
        "checks": checks,
    }
