"""Utilization endpoints (Phase 4).

GET /api/utilization                per-resource metric stats (avg/min/max/
                                    P95/stddev) + cost over the same window,
                                    with heuristic evidence signals
GET /api/utilization/{resource_id}  one resource: stats + daily series

Evidence only — this layer never produces recommendations.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from costlab.analytics import utilization as utilization_analytics
from costlab.api.deps import PaginationDep, SessionDep, UtilizationFiltersDep
from costlab.schemas.resources import UtilizationPoint
from costlab.schemas.utilization import (
    UtilizationDetailResponse,
    UtilizationItem,
    UtilizationListResponse,
)

router = APIRouter(prefix="/api/utilization", tags=["utilization"])


def _item(row: utilization_analytics.UtilizationRow) -> UtilizationItem:
    return UtilizationItem(
        resource_id=row.resource_id,
        resource_name=row.resource_name,
        resource_type=row.resource_type,
        service_id=row.service_id,
        service_name=row.service_name,
        project_id=row.project_id,
        project_name=row.project_name,
        environment=row.environment,  # type: ignore[arg-type]  # enumerated column
        region=row.region,
        window=row.window,
        metrics=row.metrics,
        missing_metrics=row.missing_metrics,
        avg_cpu=row.avg_cpu,
        cost_in_window=row.cost_in_window,
        cost_credits_in_window=row.cost_credits_in_window,
        cost_net_in_window=row.cost_net_in_window,
        signals=row.signals,
    )


@router.get("", response_model=UtilizationListResponse)
def list_utilization(
    session: SessionDep,
    utilization_filters: UtilizationFiltersDep,
    pagination: PaginationDep,
) -> UtilizationListResponse:
    rows, pagination_out, counts, window = utilization_analytics.list_utilization(
        session, utilization_filters, pagination.page, pagination.page_size
    )
    return UtilizationListResponse(
        window=window,
        pagination=pagination_out,
        signal_counts=counts,
        items=[_item(row) for row in rows],
    )


@router.get("/{resource_id}", response_model=UtilizationDetailResponse)
def get_utilization(
    session: SessionDep,
    resource_id: str,
    utilization_filters: UtilizationFiltersDep,
) -> UtilizationDetailResponse:
    row = utilization_analytics.get_utilization_detail(session, resource_id, utilization_filters)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} was not found.")
    series: list[UtilizationPoint] = utilization_analytics.get_utilization_series(
        session, resource_id, row.window
    )
    return UtilizationDetailResponse(
        resource_id=row.resource_id,
        resource_name=row.resource_name,
        resource_type=row.resource_type,
        service_id=row.service_id,
        service_name=row.service_name,
        project_id=row.project_id,
        project_name=row.project_name,
        environment=row.environment,  # type: ignore[arg-type]  # enumerated column
        region=row.region,
        machine_type=row.machine_type,
        window=row.window,
        metrics=row.metrics,
        missing_metrics=row.missing_metrics,
        cost_in_window=row.cost_in_window,
        cost_credits_in_window=row.cost_credits_in_window,
        cost_net_in_window=row.cost_net_in_window,
        signals=row.signals,
        series=series,
    )
