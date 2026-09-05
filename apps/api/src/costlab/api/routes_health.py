"""Health and readiness endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from costlab.api.deps import SessionDep
from costlab.config import get_settings
from costlab.schemas.cost import HealthOut, ReadyOut

logger = logging.getLogger("costlab.health")
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    """Liveness: the process is up. Does not touch the database."""
    settings = get_settings()
    return HealthOut(
        status="ok",
        service="cloud-cost-lab-api",
        version=settings.api_version,
        demo_mode=settings.demo_mode,
    )


@router.get("/ready", response_model=ReadyOut)
def ready(session: SessionDep) -> ReadyOut:
    """Readiness: the API can serve data (database reachable)."""
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        logger.error("readiness check failed: database is not reachable")
        raise HTTPException(status_code=503, detail="Database is not reachable.") from None
    return ReadyOut(status="ready", database="ok")
