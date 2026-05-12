from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PredictionDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    batch_id: int
    document_id: int
    label_id: int
    label: str
    confidence: float
    top5: list[Any]
    all_probs: dict[str, Any]
    model_sha256: str
    overlay_bucket: str
    overlay_path: str
    relabeled_by: str | None
    request_id: str
    created_at: datetime
