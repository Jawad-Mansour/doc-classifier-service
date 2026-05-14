"""
FastAPI application factory.

Initializes the FastAPI app with middleware, exception handlers, and routers.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
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
from app.db.session import dispose_engine


logger = logging.getLogger("app.main")

ExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Applies:
    1. Middleware (CORS, request ID, security headers)
    2. Exception handlers
    3. Router registration
    4. Startup/shutdown events
    """
    configure_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description="ML-powered document classification service",
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        debug=settings.DEBUG,
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

    app.add_exception_handler(
        StarletteHTTPException,
        cast(ExceptionHandler, http_exception_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, validation_exception_handler),
    )
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(api_router)

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting application")
        await init_app()
        await check_policies_initialized()
        redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=False)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down application")
        await dispose_engine()

    return app


# Create app instance
app = create_app()
