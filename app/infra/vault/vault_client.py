from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class VaultClient:
    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        timeout: float = 3.0,
    ) -> None:
        self.url = (url or settings.VAULT_URL).rstrip("/")
        self.token = token or settings.VAULT_TOKEN
        self.timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Vault-Token": self.token}

    def is_available(self) -> bool:
        try:
            response = httpx.get(
                f"{self.url}/v1/sys/health",
                headers=self._headers,
                timeout=self.timeout,
            )
        except httpx.HTTPError:
            return False
        return response.status_code in {200, 429, 472, 473}

    def read_secret(self, path: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.url}/v1/{path.lstrip('/')}",
            headers=self._headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", {})
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return dict(data["data"])
        if isinstance(data, dict):
            return dict(data)
        return {}

    def write_secret(self, path: str, data: dict[str, Any]) -> None:
        secret_path = path.lstrip("/")
        payload = {"data": data} if "/data/" in secret_path else data
        response = httpx.post(
            f"{self.url}/v1/{secret_path}",
            headers=self._headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()


vault_client = VaultClient()
