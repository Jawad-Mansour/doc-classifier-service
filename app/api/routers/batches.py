"""Batch viewing and management routes."""

from fastapi import APIRouter, Depends, Path

from app.api.deps.permissions import require_permission
from app.api.schemas import BatchResponse
from app.auth.casbin import RESOURCE_BATCHES, ACTION_READ
from app.auth.users import UserRead
from app.services.batch_service import get_batch, list_batches

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("", response_model=list[BatchResponse])
async def list_batches_route(
    user: UserRead = Depends(require_permission(RESOURCE_BATCHES, ACTION_READ)),
) -> list[BatchResponse]:
    """List all batches."""
    return await list_batches()


@router.get("/{bid}", response_model=BatchResponse)
async def get_batch_route(
    bid: str = Path(...),
    user: UserRead = Depends(require_permission(RESOURCE_BATCHES, ACTION_READ)),
) -> BatchResponse:
    """Get a single batch by ID."""
    return await get_batch(bid)
