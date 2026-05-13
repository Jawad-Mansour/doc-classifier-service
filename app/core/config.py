"""
Application configuration.

Settings for database, logging, environment variables, etc.
"""

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    APP_NAME: str = Field(default="Document Classifier API")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)

    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    DATABASE_URL: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./test.db"))
    LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    REDIS_URL: str | None = Field(default_factory=lambda: os.getenv("REDIS_URL"))


settings = Settings()
