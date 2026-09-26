"""Forecast + anomaly endpoints (Phase 7).

GET /api/forecast   30-day cost projection (moving average + linear trend),
                    expected/lower/upper bounds + confidence — estimates
                    with an explicit range, never exact values (CLAUDE.md §27)
GET /api/anomalies  point-level unexpected cost increases (rolling average +
                    z-score) with severity and confidence (§28)
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from costlab.analytics.anomalies import DEFAULT_MIN_Z, detect_anomalies
from costlab.analytics.forecasting import build_forecast
from costlab.api.deps import SessionDep
from costlab.db.models import Resource
from costlab.schemas.cost import CostFilters, PaginationOut
from costlab.schemas.forecast import (
    AnomalyItem,
    AnomalyListResponse,
    AnomalySummary,
    ForecastResponse,
)

router_forecast = APIRouter(prefix="/api/forecast", tags=["forecast"])
router_anomalies = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


def _cost_filters(
    start_date: date | None,
    end_date: date | None,
    project_id: str | None,
    service: str | None,
    environment: str | None,
    region: str | None,
) -> CostFilters:
    try:
        return CostFilters(
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            service=service,
            environment=environment,  # type: ignore[arg-type]  # validated by schema
            region=region,
        )
    except Exception as exc:  # noqa: BLE001  # surface as 422, not 500
        raise HTTPException(status_code=422, detail=f"Invalid filters: {exc}") from exc


@router_forecast.get("", response_model=ForecastResponse)
def get_forecast(
    session: SessionDep,
    horizon_days: Annotated[int, Query(ge=7, le=90, description="Days to project.")] = 30,
    project_id: Annotated[str | None, Query(max_length=64)] = None,
    service: Annotated[str | None, Query(max_length=64)] = None,
    environment: Annotated[str | None, Query(max_length=16)] = None,
    region: Annotated[str | None, Query(max_length=64)] = None,
) -> ForecastResponse:
    filters = _cost_filters(None, None, project_id, service, environment, region)
    result: dict[str, Any] = build_forecast(session, filters, horizon_days)
    return ForecastResponse(**result)


@router_anomalies.get("", response_model=AnomalyListResponse)
def get_anomalies(
    session: SessionDep,
    min_z_score: Annotated[
        float, Query(ge=1.0, le=10.0, description="Minimum z-score (default 2.0).")
    ] = DEFAULT_MIN_Z,
    severity: Annotated[str | None, Query(description="LOW | MEDIUM | HIGH")] = None,
    project_id: Annotated[str | None, Query(max_length=64)] = None,
    service: Annotated[str | None, Query(max_length=64)] = None,
    environment: Annotated[str | None, Query(max_length=16)] = None,
    resource_id: Annotated[str | None, Query(max_length=128)] = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AnomalyListResponse:
    if severity and severity not in ("LOW", "MEDIUM", "HIGH"):
        raise HTTPException(status_code=422, detail=f"Invalid severity: {severity!r}")

    hits = detect_anomalies(session, min_z_score=min_z_score)

    if severity:
        hits = [hit for hit in hits if hit.severity == severity]
    if project_id:
        hits = [hit for hit in hits if hit.project_id == project_id]
    if service:
        hits = [hit for hit in hits if hit.service_id == service]
    if environment:
        # Environment is a resource/project attribute; resolve to project ids.
        env_projects = {
            row[0]
            for row in session.execute(
                select(Resource.project_id).where(Resource.environment == environment)
            ).all()
        }
        hits = [hit for hit in hits if hit.project_id in env_projects]
    if resource_id:
        hits = [hit for hit in hits if hit.resource_id == resource_id]

    total = len(hits)
    start = (page - 1) * page_size
    page_items = hits[start : start + page_size]
    by_severity: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    by_service: dict[str, int] = {}
    for hit in hits:
        by_severity[hit.severity] += 1
        by_service[hit.service_id] = by_service.get(hit.service_id, 0) + 1

    return AnomalyListResponse(
        summary=AnomalySummary(total=total, by_severity=by_severity, by_service=by_service),
        pagination=PaginationOut(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
        items=[AnomalyItem(**hit.as_dict()) for hit in page_items],
    )
