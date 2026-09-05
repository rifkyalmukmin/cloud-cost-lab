"""Structured error responses (CLAUDE.md §39).

Every error — validation, HTTP, or unhandled — is returned as
{"error": {"code", "message", "request_id", ...}} and logged with the request id.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from costlab.api.middleware import REQUEST_ID_HEADER
from costlab.logging_config import request_id_var

logger = logging.getLogger("costlab.errors")


def _request_id(request: Request) -> str | None:
    """Request id from the context var, then request.state, then the raw header
    (the outermost 500 handler runs outside the request-id middleware)."""
    return (
        request_id_var.get()
        or getattr(request.state, "request_id", None)
        or request.headers.get(REQUEST_ID_HEADER)
    )


def _error_body(
    code: str, message: str, request_id: str | None, details: list | None = None
) -> dict:
    error: dict = {"code": code, "message": message, "request_id": request_id}
    if details:
        error["details"] = details
    return {"error": error}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # pydantic v2 puts arbitrary objects in `ctx`; drop it for safe JSON encoding.
        details = [{k: v for k, v in err.items() if k != "ctx"} for err in exc.errors()]
        logger.warning(
            "request validation failed",
            extra={"operation": "validation_error", "path": request.url.path, "details": details},
        )
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                _error_body(
                    "validation_error", "Request validation failed.", _request_id(request), details
                )
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def on_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Registered for Starlette's HTTPException so it also covers framework
        # 404s for unmatched routes (FastAPI's HTTPException subclasses it).
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", str(exc.detail), _request_id(request)),
        )

    @app.exception_handler(Exception)
    async def on_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        # Log the traceback server-side; return a generic message to the client.
        logger.exception(
            "unhandled error",
            extra={
                "operation": "unhandled_error",
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "Internal server error.", _request_id(request)),
        )
