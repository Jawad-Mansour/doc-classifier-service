"""
Security settings and auth configuration.
"""

import os
from typing import Any
from pydantic import BaseModel, Field, field_validator
from app.core.config import settings


def _normalize_origins(value: Any) -> list[str]:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    if isinstance(value, list):
        return [origin.strip() for origin in value if isinstance(origin, str) and origin.strip()]
    return []


class SecuritySettings(BaseModel):
    """Security configuration loaded from environment variables."""

    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "change-me-in-production"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_AUDIENCE: list[str] = Field(default_factory=lambda: ["doc-classifier-service"])

    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: _normalize_origins(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080")))
    ALLOW_CREDENTIALS: bool = Field(default_factory=lambda: os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true")
    ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"])
    ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["Authorization", "Content-Type", "X-Request-ID"])

    CASBIN_ENABLE: bool = False
    CASBIN_MODEL_PATH: str = "app/auth/rbac_model.conf"
    CASBIN_POLICY_PATH: str = "app/auth/rbac_policy.csv"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def normalize_origins(cls, value: Any) -> list[str]:
        return _normalize_origins(value)

    def validate_settings(self) -> None:
        if settings.DEBUG:
            return

        if self.SECRET_KEY == "change-me-in-production":
            raise RuntimeError(
                "SECRET_KEY must be configured before startup in non-debug mode."
            )

        if not self.ALLOWED_ORIGINS:
            raise RuntimeError(
                "ALLOWED_ORIGINS must contain at least one origin in non-debug mode."
            )

        if "*" in self.ALLOWED_ORIGINS:
            raise RuntimeError(
                "Wildcard origins are not allowed in ALLOWED_ORIGINS for non-debug mode."
            )


def get_cors_origins() -> list[str]:
    origins = [origin for origin in security_settings.ALLOWED_ORIGINS if origin]
    return origins or ["http://localhost:3000"]


security_settings = SecuritySettings()
