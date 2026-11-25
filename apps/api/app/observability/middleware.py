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
        path = _route_template(request)
        status = response.status_code

        labels = {"method": method, "path": path, "status": str(status)}

        metrics.increment("http_requests_total", labels=labels)
        metrics.observe("http_request_duration_seconds", duration, labels={"path": path})

        return response


def _route_template(request: Request) -> str:
    """Use the matched route template so resource ids do not explode label cardinality."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return "unmatched"
