from pydantic import BaseModel, ConfigDict


class TopKPrediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    label_id: int
    label: str
    confidence: float


class PredictionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    label_id: int
    label: str
    confidence: float
    top5: list[TopKPrediction]
    all_probs: dict[str, float]
    model_sha256: str
