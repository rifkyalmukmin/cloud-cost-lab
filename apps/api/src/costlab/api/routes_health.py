"""Health, readiness and data-freshness endpoints."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy import text as sql_text

from costlab.analytics.freshness import compute_freshness
from costlab.api.deps import SessionDep
from costlab.config import get_settings
from costlab.db.models import CostRecord
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
        session.execute(sql_text("SELECT 1"))
    except Exception:
        logger.error("readiness check failed: database is not reachable")
        raise HTTPException(status_code=503, detail="Database is not reachable.") from None
    return ReadyOut(status="ready", database="ok")


@router.get("/api/freshness")
def freshness(session: SessionDep) -> dict[str, Any]:
    """Data freshness (CLAUDE.md §41): FRESH / STALE / UNKNOWN with the age
    of the newest data day. Stale data is never presented as current."""
    settings = get_settings()
    newest_data_date = session.execute(select(func.max(CostRecord.usage_date))).scalar_one()
    result = compute_freshness(
        newest_data_date,
        now=datetime.now(UTC),
        max_age_hours=settings.freshness_max_hours,
    )
    return result.as_dict()
