"""
Test fixtures for API tests.

Provides:
- FastAPI TestClient
- Mock services
- Test database
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client (triggers startup/shutdown lifespan)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def request_headers() -> dict:
    """Standard request headers with request ID."""
    return {
        "X-Request-ID": "test-request-123",
        "Content-Type": "application/json",
    }
