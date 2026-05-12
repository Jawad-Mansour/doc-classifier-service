"""Application startup checks and initialization."""

from app.auth.casbin import get_casbin_enforcer
from app.core.security import security_settings
from app.services.role_service import RoleService


async def check_policies_initialized() -> None:
    """Check that RBAC policies are initialized.

    Raises:
        RuntimeError: If no policies are found in the database.
    """
    enforcer = get_casbin_enforcer()
    policies = enforcer.get_policy()

    if not policies:
        raise RuntimeError(
            "RBAC policies table is empty. "
            "Please run: python scripts/seed_policies.py"
        )


async def init_app() -> None:
    """Initialize application at startup."""
    security_settings.validate_settings()
    await RoleService.seed_default_policies()
