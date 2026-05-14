"""Prediction-related endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.permissions import require_permission
from app.api.schemas import PredictionResponse, PredictionUpdateRequest
from app.auth.casbin import RESOURCE_PREDICTIONS, ACTION_READ, ACTION_UPDATE
from app.auth.users import UserRead
from app.db.session import get_session
from app.exceptions import InvalidLabel, PredictionNotFound, UnauthorizedRelabel
from app.services import cache_service
from app.services.prediction_service import get_recent, list_predictions, relabel
from fastapi_cache.decorator import cache

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/recent", response_model=list[PredictionResponse])
@cache(expire=60, namespace=cache_service.PREDICTIONS_RECENT_NAMESPACE)
async def get_recent_predictions(
    user: UserRead = Depends(require_permission(RESOURCE_PREDICTIONS, ACTION_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[PredictionResponse]:
    return await get_recent(session)


@router.get("/batch/{batch_id}", response_model=list[PredictionResponse])
async def get_predictions_for_batch(
    batch_id: int = Path(...),
    user: UserRead = Depends(require_permission(RESOURCE_PREDICTIONS, ACTION_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[PredictionResponse]:
    del user
    return await list_predictions(session, batch_id)


@router.patch("/{id}", response_model=PredictionResponse)
async def update_prediction(
    request: PredictionUpdateRequest,
    id: int = Path(...),
    user: UserRead = Depends(require_permission(RESOURCE_PREDICTIONS, ACTION_UPDATE)),
    session: AsyncSession = Depends(get_session),
) -> PredictionResponse:
    try:
        return await relabel(session, id, request.new_label, user.email, user.role or "")
    except PredictionNotFound:
        raise HTTPException(status_code=404, detail="Prediction not found")
    except UnauthorizedRelabel:
        raise HTTPException(status_code=403, detail="Cannot relabel predictions with confidence >= 0.7")
    except InvalidLabel as e:
        raise HTTPException(status_code=400, detail=str(e))
