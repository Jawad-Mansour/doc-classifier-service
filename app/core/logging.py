"""Logging helpers with request ID propagation."""

import logging
import sys
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="unknown")


class RequestIDFilter(logging.Filter):
    """Attach the current request ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("unknown")
        return True


def configure_logging() -> None:
    """Configure logging with a request ID filter and sane defaults."""
    root_logger = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
    )

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.addFilter(RequestIDFilter())
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            handler.addFilter(RequestIDFilter())

    root_logger.setLevel(logging.INFO)
