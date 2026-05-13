"""Application startup checks and initialization."""

from app.auth.casbin import ROLE_ADMIN, ROLE_AUDITOR, ROLE_REVIEWER, get_casbin_enforcer
from app.core.config import settings
from app.core.security import security_settings
from app.db.session import AsyncSessionLocal
from app.infra.vault import vault_client
from app.services.role_service import RoleService
from app.services.user_service import seed_demo_user


JWT_SECRET_FIELD = "jwt_secret_key"
DATABASE_PASSWORD_FIELD = "database_password"
MINIO_SECRET_KEY_FIELD = "minio_secret_key"
SFTP_PASSWORD_FIELD = "sftp_password"
REQUIRED_VAULT_FIELDS = {
    JWT_SECRET_FIELD,
    DATABASE_PASSWORD_FIELD,
    MINIO_SECRET_KEY_FIELD,
    SFTP_PASSWORD_FIELD,
}


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
    configure_app_secrets()
    security_settings.validate_settings()
    await RoleService.seed_default_policies()
    await seed_demo_users()


def configure_app_secrets() -> None:
    if not settings.REQUIRE_VAULT:
        return

    if not vault_client.is_available():
        raise RuntimeError("Vault is required but is not reachable.")

    secret = _read_or_seed_app_secret()
    missing = [
        field
        for field in REQUIRED_VAULT_FIELDS
        if not isinstance(secret.get(field), str) or not secret.get(field)
    ]
    if missing:
        raise RuntimeError(
            f"Vault secret {settings.VAULT_SECRET_BASE_PATH!r} is missing required fields: {missing}."
        )

    jwt_secret = secret.get(JWT_SECRET_FIELD)
    settings.JWT_SECRET_KEY = jwt_secret
    security_settings.set_secret_key(jwt_secret)
    settings.set_database_password(secret[DATABASE_PASSWORD_FIELD])
    settings.MINIO_SECRET_KEY = secret[MINIO_SECRET_KEY_FIELD]
    settings.SFTP_PASSWORD = secret[SFTP_PASSWORD_FIELD]


def configure_jwt_secret() -> None:
    configure_app_secrets()


def _read_or_seed_app_secret() -> dict:
    try:
        secret = vault_client.read_secret(settings.VAULT_SECRET_BASE_PATH)
    except Exception:
        secret = {}

    missing = REQUIRED_VAULT_FIELDS - set(secret)
    if missing:
        seeded = {
            JWT_SECRET_FIELD: settings.JWT_SECRET_KEY or security_settings.SECRET_KEY,
            DATABASE_PASSWORD_FIELD: settings.DATABASE_PASSWORD or "app",
            MINIO_SECRET_KEY_FIELD: settings.MINIO_SECRET_KEY,
            SFTP_PASSWORD_FIELD: settings.SFTP_PASSWORD,
        }
        seeded.update(secret)
        vault_client.write_secret(settings.VAULT_SECRET_BASE_PATH, seeded)
        secret = vault_client.read_secret(settings.VAULT_SECRET_BASE_PATH)

    return secret


async def seed_demo_users() -> None:
    if not (settings.DEBUG and settings.SEED_DEMO_USERS):
        return

    demo_users = [
        (settings.DEMO_ADMIN_EMAIL, settings.DEMO_ADMIN_PASSWORD, ROLE_ADMIN),
        (settings.DEMO_REVIEWER_EMAIL, settings.DEMO_REVIEWER_PASSWORD, ROLE_REVIEWER),
        (settings.DEMO_AUDITOR_EMAIL, settings.DEMO_AUDITOR_PASSWORD, ROLE_AUDITOR),
    ]
    async with AsyncSessionLocal() as session:
        for email, password, role in demo_users:
            await seed_demo_user(session, email, password, role)
        await session.commit()
