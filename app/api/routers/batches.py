"""Batch viewing routes."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.permissions import require_permission
from app.api.schemas import BatchResponse
from app.auth.casbin import RESOURCE_BATCHES, ACTION_READ
from app.auth.users import UserRead
from app.db.session import get_session
from app.exceptions import BatchNotFound
from app.services import cache_service
from app.services.batch_service import get_batch, list_batches
from fastapi_cache.decorator import cache

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("", response_model=list[BatchResponse])
@cache(expire=60, namespace=cache_service.BATCHES_NAMESPACE)
async def list_batches_route(
    user: UserRead = Depends(require_permission(RESOURCE_BATCHES, ACTION_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[BatchResponse]:
    del user
    return [BatchResponse.model_validate(row) for row in await list_batches(session)]


@router.get("/{bid}", response_model=BatchResponse)
@cache(expire=60, namespace=cache_service.BATCH_NAMESPACE, key_builder=cache_service.batch_detail_key_builder)
async def get_batch_route(
    bid: int = Path(...),
    user: UserRead = Depends(require_permission(RESOURCE_BATCHES, ACTION_READ)),
    session: AsyncSession = Depends(get_session),
) -> BatchResponse:
    try:
        del user
        return BatchResponse.model_validate(await get_batch(session, bid))
    except BatchNotFound:
        raise HTTPException(status_code=404, detail="Batch not found")
