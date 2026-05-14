from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.api.schemas.common import ErrorResponse, HealthResponse, MessageResponse
from app.core.constants import UserRole


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: str
    status: str
    created_at: datetime


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    label: str
    confidence: float
    top5: list[Any] | None = None
    relabeled_by: str | None
    created_at: datetime


class PredictionUpdateRequest(BaseModel):
    new_label: str


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    target: str
    timestamp: datetime


class UserRoleUpdateRequest(BaseModel):
    role: UserRole


class UserRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str


class ClassificationQueuedResponse(BaseModel):
    status: str
    request_id: str
    job_id: str
    queue_job_id: str
    batch_id: int
    document_id: int
    blob_bucket: str
    blob_path: str
    original_filename: str


__all__ = [
    "AuditLogResponse",
    "BatchResponse",
    "ClassificationQueuedResponse",
    "ErrorResponse",
    "HealthResponse",
    "MessageResponse",
    "PredictionResponse",
    "PredictionUpdateRequest",
    "UserRoleResponse",
    "UserRoleUpdateRequest",
]
