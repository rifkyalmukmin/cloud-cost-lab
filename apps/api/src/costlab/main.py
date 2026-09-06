"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from costlab import __version__
from costlab.api.errors import install_error_handlers
from costlab.api.middleware import RequestContextMiddleware
from costlab.api.routes_cost import router as cost_router
from costlab.api.routes_health import router as health_router
from costlab.api.routes_resources import router as resources_router
from costlab.config import get_settings
from costlab.logging_config import setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Cloud Cost Lab API",
        version=__version__,
        description=(
            "GCP FinOps & Cloud Cost Optimization platform — Phase 1: mock cost "
            "analytics engine. All data is synthetic (DEMO_MODE=true)."
        ),
    )
    # The Phase 2 dashboard (apps/web) calls this API cross-origin from the browser.
    # GET-only + configured origins: no cookies, no credentials, no wildcard-with-credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["Accept"],
        allow_credentials=False,
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(cost_router)
    app.include_router(resources_router)
    return app


app = create_app()
