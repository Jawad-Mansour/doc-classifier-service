"""
API schemas (Pydantic v2 models).

Request and response models for all API endpoints.
Keep schemas thin and focused on API contracts.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="0.1.0")

    model_config = {"json_schema_extra": {"example": {"status": "healthy", "version": "0.1.0"}}}


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Machine-readable error code")
    request_id: str | None = Field(None, description="Request ID for tracing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "User not found",
                "error_code": "USER_NOT_FOUND",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(..., description="Response message")
    status: str = Field(..., description="Status code")
