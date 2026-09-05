"""Request context middleware: request id + structured access log."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from costlab.logging_config import request_id_var

logger = logging.getLogger("costlab.request")

REQUEST_ID_HEADER = "x-request-id"
REQUEST_ID_MAX_LENGTH = 64


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id to every request (client-supplied or generated),
    echo it in the response header, and log one structured line per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = raw[:REQUEST_ID_MAX_LENGTH] if raw else uuid.uuid4().hex
        # state survives into the outermost error handler (context vars do not),
        # so 500 responses can still echo a request id.
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request handled",
            extra={
                "operation": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
