"""Tests for RBAC permission enforcement."""

import pytest
from unittest.mock import MagicMock, patch

from app.auth.casbin import (
    ROLE_ADMIN,
    ROLE_REVIEWER,
    ROLE_AUDITOR,
    RESOURCE_USERS,
    RESOURCE_BATCHES,
    RESOURCE_PREDICTIONS,
    RESOURCE_AUDIT_LOG,
    ACTION_READ,
    ACTION_UPDATE,
    ACTION_MANAGE_ROLES,
)
from app.services.role_service import RoleService
from app.api.deps.permissions import require_admin, require_reviewer


class FakeUser:
    """Fake user for testing."""
    def __init__(self, user_id: str, role: str):
        self.id = user_id
        self.role = role


def _make_seeded_enforcer():
    """Return a real casbin enforcer with default policies loaded."""
    from casbin_sqlalchemy_adapter import Adapter
    import casbin
    from app.auth.casbin import RBAC_MODEL

    model = casbin.Model()
    model.load_model_from_text(RBAC_MODEL)
    from sqlalchemy import create_engine
    mem_engine = create_engine("sqlite:///:memory:")
    adapter = Adapter(mem_engine)
    enforcer = casbin.Enforcer(model, adapter)
    # Seed policies
    enforcer.add_policy(ROLE_ADMIN, "users", "create")
    enforcer.add_policy(ROLE_ADMIN, "users", "read")
    enforcer.add_policy(ROLE_ADMIN, "users", "update")
    enforcer.add_policy(ROLE_ADMIN, "users", "delete")
    enforcer.add_policy(ROLE_ADMIN, "users", "manage_roles")
    enforcer.add_policy(ROLE_ADMIN, "batches", "read")
    enforcer.add_policy(ROLE_ADMIN, "predictions", "read")
    enforcer.add_policy(ROLE_ADMIN, "predictions", "update")
    enforcer.add_policy(ROLE_ADMIN, "audit_log", "read")
    enforcer.add_policy(ROLE_REVIEWER, "batches", "read")
    enforcer.add_policy(ROLE_REVIEWER, "predictions", "read")
    enforcer.add_policy(ROLE_REVIEWER, "predictions", "update")
    enforcer.add_policy(ROLE_AUDITOR, "batches", "read")
    enforcer.add_policy(ROLE_AUDITOR, "audit_log", "read")
    return enforcer


def test_admin_has_user_permissions():
    """Admin should have full user management permissions."""
    enforcer = _make_seeded_enforcer()
    policies = enforcer.get_policy()

    assert [ROLE_ADMIN, RESOURCE_USERS, ACTION_READ] in policies
    assert [ROLE_ADMIN, RESOURCE_USERS, ACTION_MANAGE_ROLES] in policies
    assert enforcer.enforce(ROLE_ADMIN, RESOURCE_BATCHES, ACTION_READ)
    assert enforcer.enforce(ROLE_ADMIN, RESOURCE_PREDICTIONS, ACTION_READ)
    assert enforcer.enforce(ROLE_ADMIN, RESOURCE_PREDICTIONS, ACTION_UPDATE)


@pytest.mark.asyncio
async def test_seed_default_policies_adds_missing_admin_permissions():
    """Seeder must repair existing DB policy tables that are missing newer policies."""
    with patch("app.services.role_service.get_casbin_enforcer") as mock_get_enforcer:
        mock_enforcer = MagicMock()
        mock_get_enforcer.return_value = mock_enforcer
        mock_enforcer.add_policy.side_effect = [
            False,  # admin users create
            False,  # admin users read
            False,  # admin users update
            False,  # admin users delete
            False,  # admin users manage_roles
            True,   # admin batches read
            True,   # admin predictions read
            True,   # admin predictions update
            False,  # admin audit read
            False,  # reviewer batches read
            False,  # reviewer predictions read
            False,  # reviewer predictions update
            False,  # auditor batches read
            False,  # auditor audit read
        ]

        await RoleService.seed_default_policies()

    mock_enforcer.add_policy.assert_any_call(ROLE_ADMIN, RESOURCE_BATCHES, ACTION_READ)
    mock_enforcer.add_policy.assert_any_call(ROLE_ADMIN, RESOURCE_PREDICTIONS, ACTION_READ)
    mock_enforcer.add_policy.assert_any_call(ROLE_ADMIN, RESOURCE_PREDICTIONS, ACTION_UPDATE)
    mock_enforcer.save_policy.assert_called_once()


def test_reviewer_cannot_manage_users():
    """Reviewer should NOT have user management permissions."""
    enforcer = _make_seeded_enforcer()
    assert not enforcer.enforce(ROLE_REVIEWER, RESOURCE_USERS, ACTION_MANAGE_ROLES)


def test_auditor_has_read_only_access():
    """Auditor should have read-only access to batches and audit logs."""
    enforcer = _make_seeded_enforcer()
    assert enforcer.enforce(ROLE_AUDITOR, RESOURCE_BATCHES, ACTION_READ)
    assert enforcer.enforce(ROLE_AUDITOR, RESOURCE_AUDIT_LOG, ACTION_READ)
    assert not enforcer.enforce(ROLE_AUDITOR, RESOURCE_BATCHES, ACTION_UPDATE)


def test_require_admin_denies_non_admin():
    """require_admin should deny non-admin users."""
    user = FakeUser("user1", ROLE_REVIEWER)
    with pytest.raises(Exception):  # HTTPException
        require_admin(user)


def test_require_admin_allows_admin():
    """require_admin should allow admin users."""
    user = FakeUser("admin1", ROLE_ADMIN)
    result = require_admin(user)
    assert result.role == ROLE_ADMIN


def test_require_reviewer_allows_reviewer():
    """require_reviewer should allow reviewer users."""
    user = FakeUser("reviewer1", ROLE_REVIEWER)
    result = require_reviewer(user)
    assert result.role == ROLE_REVIEWER


def test_require_reviewer_allows_admin():
    """require_reviewer should allow admin users (role hierarchy)."""
    user = FakeUser("admin1", ROLE_ADMIN)
    result = require_reviewer(user)
    assert result.role == ROLE_ADMIN


def test_require_reviewer_denies_auditor():
    """require_reviewer should deny auditor users."""
    user = FakeUser("auditor1", ROLE_AUDITOR)
    with pytest.raises(Exception):  # HTTPException
        require_reviewer(user)


@pytest.mark.asyncio
async def test_role_service_assign_role():
    """RoleService should assign roles to users."""
    with patch("app.services.role_service.get_casbin_enforcer") as mock_get_enforcer:
        mock_enforcer = MagicMock()
        mock_get_enforcer.return_value = mock_enforcer

        await RoleService.assign_role("user1", ROLE_REVIEWER)

        mock_enforcer.delete_roles_for_user.assert_called_once_with("user1")
        mock_enforcer.add_role_for_user.assert_called_once_with("user1", ROLE_REVIEWER)
        mock_enforcer.save_policy.assert_called_once()


@pytest.mark.asyncio
async def test_role_service_toggle_role_add():
    """RoleService should add role when toggling for user without role."""
    with patch("app.services.role_service.get_casbin_enforcer") as mock_get_enforcer:
        mock_enforcer = MagicMock()
        mock_enforcer.get_roles_for_user.return_value = []
        mock_get_enforcer.return_value = mock_enforcer

        result = await RoleService.toggle_role("user1", ROLE_REVIEWER)

        assert result is True
        mock_enforcer.add_role_for_user.assert_called_once()


@pytest.mark.asyncio
async def test_role_service_toggle_role_remove():
    """RoleService should remove role when toggling for user with role."""
    with patch("app.services.role_service.get_casbin_enforcer") as mock_get_enforcer:
        mock_enforcer = MagicMock()
        mock_enforcer.get_roles_for_user.return_value = [ROLE_REVIEWER]
        mock_get_enforcer.return_value = mock_enforcer

        result = await RoleService.toggle_role("user1", ROLE_REVIEWER)

        assert result is False
        mock_enforcer.delete_roles_for_user.assert_called_once()
