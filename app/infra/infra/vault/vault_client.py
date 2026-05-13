import hvac

from app.core.config import settings


def get_vault_client():
    return hvac.Client(
        url=settings.VAULT_URL,
        token=settings.VAULT_TOKEN
    )


def get_secret(path: str, key: str):
    client = get_vault_client()

    if not client.is_authenticated():
        raise RuntimeError(
            "Vault authentication failed"
        )

    response = (
        client.secrets.kv.v2
        .read_secret_version(path=path)
    )

    return response["data"]["data"].get(key)