"""
Health check router.

Minimal, stateless endpoint for K8s probes and monitoring.
"""

from datetime import datetime

from fastapi import APIRouter

from app.api.schemas import HealthResponse

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
async def readiness_check() -> dict[str, bool]:
    """
    Readiness check.

    Placeholder: Add DB, cache, and service checks here.
    """
    # TODO: Check DB connectivity, cache, etc.
    return {"ready": True}
