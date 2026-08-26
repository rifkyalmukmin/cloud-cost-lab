from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.observability.middleware import MetricsMiddleware
from app.routers import ai, anomalies, budget, cost, forecast, health, monitoring, observability, policies, recommendations, resources, savings, utilization

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app_started",
        environment=settings.app_env,
        demo_mode=settings.demo_mode,
    )
    yield


app = FastAPI(
    title="Cloud Cost Lab API",
    description="GCP FinOps & Cloud Cost Optimization Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(cost.router)
app.include_router(resources.router)
app.include_router(utilization.router)
app.include_router(recommendations.router)
app.include_router(budget.router)
app.include_router(policies.router)
app.include_router(forecast.router)
app.include_router(anomalies.router)
app.include_router(monitoring.router)
app.include_router(observability.router)
app.include_router(savings.router)
app.include_router(ai.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": request.url.path},
    )
