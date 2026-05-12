from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions import LastAdminError, UserNotFound
from app.services import user_service


def _fake_user(role: str = "auditor", user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email="user@example.com",
        is_active=True,
        is_superuser=False,
        is_verified=False,
        role=role,
    )


# ── Test 1 ─────────────────────────────────────────────────────────────────────
async def test_toggle_role_raises_last_admin_error_when_last_admin():
    """Demoting the only admin must raise LastAdminError, no DB write occurs."""
    session = AsyncMock()
    admin = _fake_user(role="admin")

    with (
        patch("app.services.user_service.user_repository.get_by_id", return_value=admin),
        patch("app.services.user_service.user_repository.count_by_role", return_value=1),
        patch("app.services.user_service.user_repository.update_role") as mock_update,
    ):
        with pytest.raises(LastAdminError):
            await user_service.toggle_role(session, 1, "auditor", "admin@example.com")

        mock_update.assert_not_called()


# ── Test 2 ─────────────────────────────────────────────────────────────────────
async def test_toggle_role_raises_user_not_found():
    """Non-existent user_id must raise UserNotFound."""
    session = AsyncMock()

    with patch("app.services.user_service.user_repository.get_by_id", return_value=None):
        with pytest.raises(UserNotFound):
            await user_service.toggle_role(session, 999, "reviewer", "admin@example.com")


# ── Test 3 ─────────────────────────────────────────────────────────────────────
async def test_toggle_role_succeeds_when_multiple_admins():
    """Demoting an admin is allowed when 2+ admins exist; no exception raised."""
    session = AsyncMock()
    admin = _fake_user(role="admin", user_id=2)
    demoted = _fake_user(role="auditor", user_id=2)

    with (
        patch("app.services.user_service.user_repository.get_by_id", return_value=admin),
        patch("app.services.user_service.user_repository.count_by_role", return_value=2),
        patch("app.services.user_service.user_repository.update_role", return_value=demoted),
        patch("app.services.user_service.audit_service.log_event", new_callable=AsyncMock),
        patch("app.services.user_service.cache_service.invalidate_user", new_callable=AsyncMock),
    ):
        result = await user_service.toggle_role(session, 2, "auditor", "superadmin@example.com")

    assert result.role == "auditor"


# ── Test 4 ─────────────────────────────────────────────────────────────────────
async def test_toggle_role_calls_audit_and_cache_on_success():
    """Successful role change must log an audit event and invalidate the user cache."""
    session = AsyncMock()
    admin = _fake_user(role="admin", user_id=3)
    updated = _fake_user(role="reviewer", user_id=3)

    with (
        patch("app.services.user_service.user_repository.get_by_id", return_value=admin),
        patch("app.services.user_service.user_repository.count_by_role", return_value=3),
        patch("app.services.user_service.user_repository.update_role", return_value=updated),
        patch("app.services.user_service.audit_service.log_event", new_callable=AsyncMock) as mock_audit,
        patch("app.services.user_service.cache_service.invalidate_user", new_callable=AsyncMock) as mock_cache,
    ):
        await user_service.toggle_role(session, 3, "reviewer", "boss@example.com")

    mock_audit.assert_called_once_with(session, "boss@example.com", "role_change", "user:3")
    mock_cache.assert_called_once_with(3)
