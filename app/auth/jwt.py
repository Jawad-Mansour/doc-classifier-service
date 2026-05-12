"""JWT authentication setup for fastapi-users."""

from fastapi_users.authentication import JWTStrategy

from app.core.security import security_settings


def get_jwt_strategy() -> JWTStrategy:
    """Build a JWT strategy for FastAPI Users."""
    return JWTStrategy(
        secret=security_settings.SECRET_KEY,
        lifetime_seconds=security_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        token_audience=["doc-classifier-service"],
        algorithm=security_settings.ALGORITHM,
    )
