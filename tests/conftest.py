"""Root-level test fixtures shared across all test packages."""

import os

# Set before any app imports so Settings() and SecuritySettings() pick them up
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-demo-minimum-32-chars-x")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client (triggers startup/shutdown lifespan)."""
    with TestClient(app) as c:
        yield c
