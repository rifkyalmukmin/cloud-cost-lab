"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from costlab import __version__
from costlab.api.errors import install_error_handlers
from costlab.api.middleware import RequestContextMiddleware
from costlab.api.routes_ai import router as ai_router
from costlab.api.routes_cost import router as cost_router
from costlab.api.routes_forecast import router_anomalies, router_forecast
from costlab.api.routes_governance import router_budget, router_policies
from costlab.api.routes_health import router as health_router
from costlab.api.routes_recommendations import router as recommendations_router
from costlab.api.routes_resources import router as resources_router
from costlab.api.routes_utilization import router as utilization_router
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
    # The dashboard (apps/web) calls this API cross-origin from the browser.
    # GET + POST (Phase 6 budget creation) on configured origins only: no
    # cookies, no credentials, no wildcard-with-credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept"],
        allow_credentials=False,
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(cost_router)
    app.include_router(resources_router)
    app.include_router(utilization_router)
    app.include_router(recommendations_router)
    app.include_router(router_budget)
    app.include_router(router_policies)
    app.include_router(router_forecast)
    app.include_router(router_anomalies)
    app.include_router(ai_router)
    return app


app = create_app()
