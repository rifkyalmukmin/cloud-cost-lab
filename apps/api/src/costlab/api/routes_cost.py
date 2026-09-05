"""Cost API endpoints (Phase 1 scope).

GET /api/cost                 paginated cost records + filtered summary
GET /api/cost/trend           daily / weekly / monthly buckets
GET /api/cost/by-service      breakdown by service with share of total
GET /api/cost/by-project      breakdown by project with share of total
GET /api/cost/by-environment  breakdown by environment with share of total

Period semantics: start_date/end_date default to the available data bounds —
never the wall clock (see analytics.resolve_period).
"""

from __future__ import annotations

import math
from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Query

from costlab.analytics import cost as cost_analytics
from costlab.api.deps import CostFiltersDep, PaginationDep, SessionDep
from costlab.schemas.common import Environment, Granularity
from costlab.schemas.cost import (
    CostRecordOut,
    CostRecordsResponse,
    CostSummaryOut,
    EnvironmentBreakdownResponse,
    EnvironmentBreakdownRowOut,
    PaginationOut,
    PeriodOut,
    ProjectBreakdownResponse,
    ProjectBreakdownRowOut,
    ServiceBreakdownResponse,
    ServiceBreakdownRowOut,
    TrendPointOut,
    TrendResponse,
)

router = APIRouter(prefix="/api/cost", tags=["cost"])

EMPTY_SUMMARY = CostSummaryOut(cost=0.0, credits=0.0, net_cost=0.0)


def _share_pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


def _empty_period(filters) -> PeriodOut:
    """Fallback period for an empty database (bounds are unknown)."""
    return PeriodOut(start=filters.start_date or date.min, end=filters.end_date or date.min)


@router.get("", response_model=CostRecordsResponse)
def list_cost_records(
    session: SessionDep, filters: CostFiltersDep, pagination: PaginationDep
) -> CostRecordsResponse:
    period = cost_analytics.resolve_period(session, filters)
    if period is None:
        return CostRecordsResponse(
            period=_empty_period(filters),
            pagination=PaginationOut(
                page=pagination.page, page_size=pagination.page_size, total_items=0, total_pages=0
            ),
            summary=EMPTY_SUMMARY,
            items=[],
        )
    rows, total_items = cost_analytics.list_cost_records(
        session, filters, pagination.page, pagination.page_size
    )
    summary = cost_analytics.cost_summary(session, filters)
    return CostRecordsResponse(
        period=PeriodOut(start=period[0], end=period[1]),
        pagination=PaginationOut(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items,
            total_pages=math.ceil(total_items / pagination.page_size),
        ),
        summary=CostSummaryOut(
            cost=summary.cost, credits=summary.credits, net_cost=summary.net_cost
        ),
        items=[CostRecordOut(**row.__dict__) for row in rows],
    )


@router.get("/trend", response_model=TrendResponse)
def cost_trend(
    session: SessionDep,
    filters: CostFiltersDep,
    granularity: Annotated[Granularity, Query(description="day | week | month")] = "day",
) -> TrendResponse:
    period = cost_analytics.resolve_period(session, filters)
    if period is None:
        return TrendResponse(period=_empty_period(filters), granularity=granularity, points=[])
    points = cost_analytics.cost_trend(session, filters, granularity)
    return TrendResponse(
        period=PeriodOut(start=period[0], end=period[1]),
        granularity=granularity,
        points=[
            TrendPointOut(period=p.period, cost=p.cost, credits=p.credits, net_cost=p.net_cost)
            for p in points
        ],
    )


@router.get("/by-service", response_model=ServiceBreakdownResponse)
def cost_by_service(session: SessionDep, filters: CostFiltersDep) -> ServiceBreakdownResponse:
    period = cost_analytics.resolve_period(session, filters)
    if period is None:
        return ServiceBreakdownResponse(period=_empty_period(filters), total=EMPTY_SUMMARY, rows=[])
    rows = cost_analytics.cost_by_service(session, filters)
    total = cost_analytics.cost_summary(session, filters)
    return ServiceBreakdownResponse(
        period=PeriodOut(start=period[0], end=period[1]),
        total=CostSummaryOut(cost=total.cost, credits=total.credits, net_cost=total.net_cost),
        rows=[
            ServiceBreakdownRowOut(
                service=row.key,
                service_name=row.label,
                cost=row.cost,
                credits=row.credits,
                net_cost=row.net_cost,
                share_pct=_share_pct(row.cost, total.cost),
            )
            for row in rows
        ],
    )


@router.get("/by-project", response_model=ProjectBreakdownResponse)
def cost_by_project(session: SessionDep, filters: CostFiltersDep) -> ProjectBreakdownResponse:
    period = cost_analytics.resolve_period(session, filters)
    if period is None:
        return ProjectBreakdownResponse(period=_empty_period(filters), total=EMPTY_SUMMARY, rows=[])
    rows = cost_analytics.cost_by_project(session, filters)
    total = cost_analytics.cost_summary(session, filters)
    return ProjectBreakdownResponse(
        period=PeriodOut(start=period[0], end=period[1]),
        total=CostSummaryOut(cost=total.cost, credits=total.credits, net_cost=total.net_cost),
        rows=[
            ProjectBreakdownRowOut(
                project_id=row.key,
                project_name=row.label,
                cost=row.cost,
                credits=row.credits,
                net_cost=row.net_cost,
                share_pct=_share_pct(row.cost, total.cost),
            )
            for row in rows
        ],
    )


@router.get("/by-environment", response_model=EnvironmentBreakdownResponse)
def cost_by_environment(
    session: SessionDep, filters: CostFiltersDep
) -> EnvironmentBreakdownResponse:
    period = cost_analytics.resolve_period(session, filters)
    if period is None:
        return EnvironmentBreakdownResponse(
            period=_empty_period(filters), total=EMPTY_SUMMARY, rows=[]
        )
    rows = cost_analytics.cost_by_environment(session, filters)
    total = cost_analytics.cost_summary(session, filters)
    return EnvironmentBreakdownResponse(
        period=PeriodOut(start=period[0], end=period[1]),
        total=CostSummaryOut(cost=total.cost, credits=total.credits, net_cost=total.net_cost),
        rows=[
            EnvironmentBreakdownRowOut(
                environment=cast(Environment, row.key),  # column only stores enumerated values
                cost=row.cost,
                credits=row.credits,
                net_cost=row.net_cost,
                share_pct=_share_pct(row.cost, total.cost),
            )
            for row in rows
        ],
    )
