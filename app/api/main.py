"""
API router registration.

Single point for composing all routers with consistent prefix and tags.
"""

from fastapi import APIRouter

from app.api.routers import auth, health, users, batches, audit, predictions

api_router = APIRouter(prefix="/api/v1")

# Register routers
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(batches.router)
api_router.include_router(predictions.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
