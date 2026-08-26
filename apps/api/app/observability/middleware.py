"""Request metrics middleware.

Tracks http_requests_total and http_request_duration_seconds for all endpoints.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.metrics import metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time
        method = request.method
        path = request.url.path
        status = response.status_code

        labels = {"method": method, "path": path, "status": str(status)}

        metrics.increment("http_requests_total", labels=labels)
        metrics.observe("http_request_duration_seconds", duration, labels={"path": path})

        return response
