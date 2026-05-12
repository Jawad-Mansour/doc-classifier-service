"""Prediction-related endpoints."""

from fastapi import APIRouter, Depends, Path

from app.api.deps.permissions import require_permission
from app.api.schemas import PredictionResponse, PredictionUpdateRequest
from app.auth.casbin import RESOURCE_PREDICTIONS, ACTION_READ, ACTION_UPDATE
from app.auth.users import UserRead
from app.services.prediction_service import get_recent, relabel

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/recent", response_model=list[PredictionResponse])
async def get_recent_predictions(
    user: UserRead = Depends(require_permission(RESOURCE_PREDICTIONS, ACTION_READ)),
) -> list[PredictionResponse]:
    """Return recent predictions."""
    return await get_recent()


@router.patch("/{id}", response_model=PredictionResponse)
async def update_prediction(
    request: PredictionUpdateRequest,
    id: str = Path(...),
    user: UserRead = Depends(require_permission(RESOURCE_PREDICTIONS, ACTION_UPDATE)),
) -> PredictionResponse:
    """Relabel a prediction."""
    return await relabel(id, request.new_label)
