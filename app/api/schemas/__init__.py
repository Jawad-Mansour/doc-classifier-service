from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.api.schemas.common import ErrorResponse, HealthResponse, MessageResponse


class BatchResponse(BaseModel):
    id: int
    request_id: str
    status: str
    created_at: datetime


class PredictionResponse(BaseModel):
    id: int
    batch_id: int
    label: str
    confidence: float
    relabeled_by: str | None
    created_at: datetime


class PredictionUpdateRequest(BaseModel):
    new_label: str


class AuditLogResponse(BaseModel):
    id: int
    actor: str
    action: str
    target: str
    timestamp: datetime


class UserRoleUpdateRequest(BaseModel):
    role: str


class UserRoleResponse(BaseModel):
    id: int
    email: str
    role: str


__all__ = [
    "AuditLogResponse",
    "BatchResponse",
    "ErrorResponse",
    "HealthResponse",
    "MessageResponse",
    "PredictionResponse",
    "PredictionUpdateRequest",
    "UserRoleResponse",
    "UserRoleUpdateRequest",
]
