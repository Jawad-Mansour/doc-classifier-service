import pytest
import importlib

from app.core import startup
from app.core.security import security_settings
from app.infra.vault.vault_client import VaultClient


vault_client_module = importlib.import_module("app.infra.vault.vault_client")


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_vault_client_reads_kv2_secret(monkeypatch):
    def fake_get(url, headers, timeout):
        return FakeResponse(200, {"data": {"data": {"jwt_secret_key": "from-vault"}}})

    monkeypatch.setattr(vault_client_module.httpx, "get", fake_get)

    client = VaultClient(url="http://vault:8200", token="root")

    assert client.read_secret("secret/data/doc-classifier") == {"jwt_secret_key": "from-vault"}


def test_vault_client_writes_kv2_secret(monkeypatch):
    captured: dict = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse(200)

    monkeypatch.setattr(vault_client_module.httpx, "post", fake_post)

    client = VaultClient(url="http://vault:8200", token="root")
    client.write_secret("secret/data/doc-classifier", {"jwt_secret_key": "from-vault"})

    assert captured == {
        "url": "http://vault:8200/v1/secret/data/doc-classifier",
        "json": {"data": {"jwt_secret_key": "from-vault"}},
    }


def test_configure_jwt_secret_reads_required_vault(monkeypatch):
    original_secret = security_settings.SECRET_KEY
    original_database_url = startup.settings.DATABASE_URL
    original_database_sync_url = startup.settings.DATABASE_SYNC_URL
    original_minio_secret = startup.settings.MINIO_SECRET_KEY
    original_sftp_password = startup.settings.SFTP_PASSWORD

    class FakeVaultClient:
        def is_available(self) -> bool:
            return True

        def read_secret(self, path: str) -> dict:
            return {
                "jwt_secret_key": "vault-secret-minimum-32-bytes",
                "database_password": "db-secret",
                "minio_secret_key": "minio-secret",
                "sftp_password": "sftp-secret",
            }

        def write_secret(self, path: str, data: dict) -> None:
            raise AssertionError("write_secret should not be called when secret exists")

    monkeypatch.setattr(startup.settings, "REQUIRE_VAULT", True)
    monkeypatch.setattr(startup.settings, "VAULT_SECRET_BASE_PATH", "secret/data/doc-classifier")
    monkeypatch.setattr(startup, "vault_client", FakeVaultClient())

    try:
        startup.configure_jwt_secret()
        assert startup.settings.JWT_SECRET_KEY == "vault-secret-minimum-32-bytes"
        assert security_settings.SECRET_KEY == "vault-secret-minimum-32-bytes"
        assert startup.settings.DATABASE_PASSWORD == "db-secret"
        assert startup.settings.MINIO_SECRET_KEY == "minio-secret"
        assert startup.settings.SFTP_PASSWORD == "sftp-secret"
    finally:
        security_settings.SECRET_KEY = original_secret
        startup.settings.DATABASE_URL = original_database_url
        startup.settings.DATABASE_SYNC_URL = original_database_sync_url
        startup.settings.MINIO_SECRET_KEY = original_minio_secret
        startup.settings.SFTP_PASSWORD = original_sftp_password


def test_configure_jwt_secret_fails_when_required_vault_unavailable(monkeypatch):
    class FakeVaultClient:
        def is_available(self) -> bool:
            return False

    monkeypatch.setattr(startup.settings, "REQUIRE_VAULT", True)
    monkeypatch.setattr(startup, "vault_client", FakeVaultClient())

    with pytest.raises(RuntimeError, match="Vault is required"):
        startup.configure_jwt_secret()


@pytest.mark.asyncio
async def test_seed_demo_users_assigns_roles_to_auth_subject(monkeypatch):
    seeded: list[tuple[str, str, str]] = []
    committed = False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def commit(self):
            nonlocal committed
            committed = True

    async def fake_seed_demo_user(session, email: str, password: str, role: str):
        seeded.append((email, password, role))

    monkeypatch.setattr(startup.settings, "DEBUG", True)
    monkeypatch.setattr(startup.settings, "SEED_DEMO_USERS", True)
    monkeypatch.setattr(startup.settings, "DEMO_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(startup.settings, "DEMO_ADMIN_PASSWORD", "Admin123!")
    monkeypatch.setattr(startup.settings, "DEMO_REVIEWER_EMAIL", "reviewer@example.com")
    monkeypatch.setattr(startup.settings, "DEMO_REVIEWER_PASSWORD", "Reviewer123!")
    monkeypatch.setattr(startup.settings, "DEMO_AUDITOR_EMAIL", "auditor@example.com")
    monkeypatch.setattr(startup.settings, "DEMO_AUDITOR_PASSWORD", "Auditor123!")
    monkeypatch.setattr(startup, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(startup, "seed_demo_user", fake_seed_demo_user)

    await startup.seed_demo_users()

    assert seeded == [
        ("admin@example.com", "Admin123!", "admin"),
        ("reviewer@example.com", "Reviewer123!", "reviewer"),
        ("auditor@example.com", "Auditor123!", "auditor"),
    ]
    assert committed is True
