"""Authentication tests for register, login, and current user."""

import uuid

from fastapi.testclient import TestClient


def test_register_login_me_flow(client: TestClient):
    payload = {"email": f"test-{uuid.uuid4().hex}@example.com", "password": "StrongPass123!"}

    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code in (200, 201)
    user_data = register_response.json()
    assert user_data["email"] == payload["email"]
    assert "id" in user_data
    assert "is_active" in user_data

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200, login_response.text
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    auth_header = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_response = client.get("/api/v1/auth/me", headers=auth_header)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == payload["email"]
    assert me_data["id"] == user_data["id"]
