"""Structured exception handlers for FastAPI."""

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.logging import request_id_ctx

logger = logging.getLogger("app.exceptions")


class ErrorResponse(BaseModel):
    status_code: int
    error: str
    detail: Any | None = None
    request_id: str | None = None


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", request_id_ctx.get("unknown"))
    body = ErrorResponse(
        status_code=exc.status_code,
        error="request_error",
        detail=exc.detail,
        request_id=request_id,
    ).model_dump()

    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", request_id_ctx.get("unknown"))
    body = ErrorResponse(
        status_code=422,
        error="validation_error",
        detail=exc.errors(),
        request_id=request_id,
    ).model_dump()

    return JSONResponse(status_code=422, content=body)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", request_id_ctx.get("unknown"))
    logger.exception("Unhandled exception during request", exc_info=exc, extra={"request_id": request_id})
    body = ErrorResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error="internal_server_error",
        detail="An unexpected error occurred. Please contact support with the request ID.",
        request_id=request_id,
    ).model_dump()

    return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=body)
