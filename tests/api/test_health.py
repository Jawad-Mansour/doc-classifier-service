"""Health endpoint tests."""

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

import app.api.routers.health as health_router


def test_health_check(client: TestClient):
    """Test health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_check(client: TestClient):
    """Test readiness endpoint."""
    health_router.collect_readiness = AsyncMock(
        return_value={
            "ready": True,
            "checks": {
                "database": True,
                "redis": True,
                "minio": True,
            },
        }
    )
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["checks"]["database"] is True


def test_request_id_passed_through(client: TestClient, request_headers: dict):
    """Test that request ID is passed through response headers."""
    response = client.get("/api/v1/health", headers=request_headers)
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-request-123"


def test_request_id_generated_if_missing(client: TestClient):
    """Test that request ID is generated if missing."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers.get("X-Request-ID", "")) > 0
