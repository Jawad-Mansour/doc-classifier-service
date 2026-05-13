"""Mock prediction service contract."""

from datetime import datetime
from app.api.schemas import PredictionResponse

async def get_recent() -> list[PredictionResponse]:
    return [
        PredictionResponse(id="pred_1", batch_id="batch_1", label="approved", confidence=0.93, predicted_at=datetime.utcnow()),
        PredictionResponse(id="pred_2", batch_id="batch_1", label="rejected", confidence=0.58, predicted_at=datetime.utcnow()),
    ]

async def relabel(prediction_id: str, new_label: str) -> PredictionResponse:
    return PredictionResponse(id=prediction_id, batch_id="batch_1", label=new_label, confidence=0.58, predicted_at=datetime.utcnow())
