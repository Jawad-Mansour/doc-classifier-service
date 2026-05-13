import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

import app.api.routers.batches as batches_router
import app.api.routers.predictions as predictions_router
import app.api.routers.users as users_router
from app.auth.users import UserRead
from app.api.deps.auth import get_current_user_with_role
from app.main import app
from app.api.schemas import PredictionResponse, UserRoleResponse, BatchResponse
from app.core import startup as startup_module


def make_user(role: str) -> UserRead:
    ids = {"admin": 1, "reviewer": 2, "auditor": 3}
    user = UserRead(
        id=ids.get(role, 99),
        email=f"{role}@example.com",
        is_active=True,
        is_superuser=(role == "admin"),
        is_verified=True,
    )
    user.role = role
    return user


@pytest.fixture(autouse=True)
def reset_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def request_headers() -> dict:
    return {
        "X-Request-ID": "test-request-123",
        "Content-Type": "application/json",
    }


def override_current_user(user: UserRead):
    # Override get_current_user_with_role so the preset role is preserved
    async def _user() -> UserRead:
        return user

    app.dependency_overrides[get_current_user_with_role] = _user


def test_unauthenticated_requests_return_401(client: TestClient):
    response = client.get("/api/v1/batches")

    assert response.status_code == 401
    assert response.json()["detail"]


def test_wrong_role_returns_403(client: TestClient):
    override_current_user(make_user("reviewer"))

    response = client.patch(
        "/api/v1/admin/users/42/role",
        json={"role": "auditor"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "request_error"


def test_admin_can_change_user_role(client: TestClient, request_headers: dict, monkeypatch):
    admin = make_user("admin")
    override_current_user(admin)

    async def mock_toggle_role(session, user_id: int, role: str, actor_email: str) -> UserRoleResponse:
        return UserRoleResponse(id=user_id, email="target@example.com", role=role)

    monkeypatch.setattr(users_router, "toggle_role", mock_toggle_role)

    response = client.patch(
        "/api/v1/admin/users/42/role",
        json={"role": "reviewer"},
        headers=request_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"id": 42, "email": "target@example.com", "role": "reviewer"}
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_reviewer_can_relabel_low_confidence_prediction(client: TestClient, request_headers: dict, monkeypatch):
    reviewer = make_user("reviewer")
    override_current_user(reviewer)

    async def mock_relabel(session, prediction_id: int, new_label: str, actor_email: str) -> PredictionResponse:
        return PredictionResponse(
            id=prediction_id,
            batch_id=1,
            label=new_label,
            confidence=0.42,
            relabeled_by=actor_email,
            created_at="2026-05-12T00:00:00Z",
        )

    monkeypatch.setattr(predictions_router, "relabel", mock_relabel)

    response = client.patch(
        "/api/v1/predictions/1",
        json={"new_label": "approved"},
        headers=request_headers,
    )

    assert response.status_code == 200
    assert response.json()["label"] == "approved"
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_auditor_cannot_relabel(client: TestClient):
    auditor = make_user("auditor")
    override_current_user(auditor)

    response = client.patch(
        "/api/v1/predictions/1",
        json={"new_label": "approved"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "request_error"


def test_me_returns_current_user(client: TestClient):
    user = make_user("reviewer")
    override_current_user(user)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "reviewer@example.com"
    assert response.json()["id"] == 2


def test_user_without_role_gets_403_on_batches(client: TestClient):
    user = make_user("auditor")
    user.role = None
    override_current_user(user)

    response = client.get("/api/v1/batches")

    assert response.status_code == 403
    assert response.json()["detail"] == "Role 'None' cannot read batches"


def test_batches_works_for_authorized_roles(client: TestClient, request_headers: dict, monkeypatch):
    reviewer = make_user("reviewer")
    override_current_user(reviewer)

    async def mock_list_batches(session) -> list[BatchResponse]:
        return [
            BatchResponse(
                id=1,
                request_id="test-request-123",
                status="pending",
                created_at="2026-05-12T00:00:00Z",
            )
        ]

    monkeypatch.setattr(batches_router, "list_batches", mock_list_batches)

    response = client.get("/api/v1/batches", headers=request_headers)

    assert response.status_code == 200
    assert response.json()[0]["id"] == 1
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_validation_errors_return_422(client: TestClient):
    reviewer = make_user("reviewer")
    override_current_user(reviewer)

    response = client.patch(
        "/api/v1/predictions/1",
        json={"label": "approved"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_request_id_appears_in_response(client: TestClient, request_headers: dict):
    reviewer = make_user("reviewer")
    override_current_user(reviewer)

    response = client.get("/api/v1/batches", headers=request_headers)
    assert response.headers["X-Request-ID"] == "test-request-123"


@pytest.mark.asyncio
async def test_casbin_policy_startup_check_fails_if_policies_empty(monkeypatch):
    # get_casbin_enforcer is a sync function; use MagicMock, not AsyncMock
    fake_enforcer = MagicMock()
    fake_enforcer.get_policy.return_value = []

    monkeypatch.setattr(startup_module, "get_casbin_enforcer", MagicMock(return_value=fake_enforcer))

    with pytest.raises(RuntimeError, match="RBAC policies table is empty"):
        await startup_module.check_policies_initialized()
