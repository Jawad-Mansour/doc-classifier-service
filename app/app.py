"""FastAPI application factory and startup."""

import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.main import api_router
from app.api.middleware.request_id import RequestIDMiddleware
from app.api.middleware.security_headers import SecurityHeadersMiddleware
from app.core.config import settings
from app.core.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging
from app.core.security import security_settings
from app.core.startup import check_policies_initialized, init_app

logger = logging.getLogger("app.app")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    configure_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=None,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=security_settings.ALLOWED_ORIGINS,
        allow_credentials=security_settings.ALLOW_CREDENTIALS,
        allow_methods=security_settings.ALLOW_METHODS,
        allow_headers=security_settings.ALLOW_HEADERS,
    )

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(api_router)

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting application")
        await init_app()
        await check_policies_initialized()

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down application")

    return app


# Create app instance
app = create_app()
