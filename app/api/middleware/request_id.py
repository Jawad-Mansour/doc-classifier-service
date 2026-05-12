"""
Request ID middleware.

Adds a unique request ID to each incoming request for distributed tracing.
"""

import uuid
from typing import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import request_id_ctx


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that adds a unique request ID to each request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)

        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        response.headers.setdefault("X-Request-ID", request_id)
        return response
