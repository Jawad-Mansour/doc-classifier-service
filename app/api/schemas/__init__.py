from datetime import datetime

from pydantic import BaseModel

from app.api.schemas.common import ErrorResponse, HealthResponse, MessageResponse


class BatchResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime


class PredictionResponse(BaseModel):
    id: str
    batch_id: str
    label: str
    confidence: float
    predicted_at: datetime


class PredictionUpdateRequest(BaseModel):
    new_label: str


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    resource: str
    timestamp: datetime
    details: dict | None = None


class UserRoleUpdateRequest(BaseModel):
    role: str


class UserRoleResponse(BaseModel):
    id: str
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
