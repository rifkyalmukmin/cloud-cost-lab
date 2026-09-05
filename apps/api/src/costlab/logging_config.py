"""Structured JSON logging (CLAUDE.md §40).

One JSON object per line on stdout, with a request id picked from the
request-scoped context var so every log line of a request is correlatable.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

# Extra keys the application may attach to log records via `extra={...}`.
_ALLOWED_EXTRAS = ("operation", "duration_ms", "method", "path", "status_code", "details")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        for key in _ALLOWED_EXTRAS:
            value = record.__dict__.get(key)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the `costlab` logger; disable uvicorn's access log (we log requests ourselves)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    costlab_logger = logging.getLogger("costlab")
    costlab_logger.handlers = [handler]
    costlab_logger.setLevel(level.upper())
    costlab_logger.propagate = False

    logging.getLogger("uvicorn.access").handlers = [logging.NullHandler()]
    logging.getLogger("uvicorn.access").propagate = False
