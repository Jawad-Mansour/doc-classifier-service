"""Direct file classification endpoint."""

import logging
from pydantic import BaseModel

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api.deps.permissions import require_permission
from app.auth.casbin import ACTION_READ, RESOURCE_PREDICTIONS
from app.auth.users import UserRead

logger = logging.getLogger("app.classify")

router = APIRouter(prefix="/classify", tags=["classify"])


class TopResult(BaseModel):
    label: str
    confidence: float


class ClassifyResponse(BaseModel):
    label: str
    confidence: float
    top5: list[TopResult]


@router.post("", response_model=ClassifyResponse)
async def classify_document(
    request: Request,
    file: UploadFile = File(...),
    user: UserRead = Depends(require_permission(RESOURCE_PREDICTIONS, ACTION_READ)),
) -> ClassifyResponse:
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Classifier model is not available — model files missing")

    data = await file.read()
    try:
        result = predictor.predict_bytes(data)
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=422, detail=f"Could not classify file: {e}")

    return ClassifyResponse(
        label=result.label,
        confidence=result.confidence,
        top5=[TopResult(label=p.label, confidence=p.confidence) for p in result.top5],
    )
