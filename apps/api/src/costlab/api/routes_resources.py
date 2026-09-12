"""Resource inventory endpoints (Phase 3).

GET /api/resources            filtered, paginated inventory with monthly cost
                              (trailing 30 days of data) and latest utilization
GET /api/resources/{id}       full detail: metadata, ownership, labels,
                              cost history, utilization series
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from costlab.analytics import resources as resource_analytics
from costlab.api.deps import PaginationDep, ResourceFiltersDep, SessionDep
from costlab.schemas.resources import (
    ResourceDetailResponse,
    ResourceItem,
    ResourceListResponse,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])


def _item(row: resource_analytics.ResourceRow) -> ResourceItem:
    return ResourceItem(
        resource_id=row.resource_id,
        resource_name=row.resource_name,
        resource_type=row.resource_type,
        service_id=row.service_id,
        service_name=row.service_name,
        project_id=row.project_id,
        project_name=row.project_name,
        region=row.region,
        zone=row.zone,
        status=row.status,
        environment=row.environment,  # type: ignore[arg-type]  # enumerated column
        machine_type=row.machine_type,
        owner=row.owner,
        team=row.team,
        application=row.application,
        labels=row.labels,
        created_at=row.created_at,
        last_seen=row.last_seen,
        monthly_cost=row.monthly_cost,
        monthly_credits=row.monthly_credits,
        monthly_net_cost=row.monthly_net_cost,
        cpu_utilization=row.cpu_utilization,
        memory_utilization=row.memory_utilization,
    )


@router.get("", response_model=ResourceListResponse)
def list_resources(
    session: SessionDep,
    resource_filters: ResourceFiltersDep,
    pagination: PaginationDep,
) -> ResourceListResponse:
    rows, pagination_out, summary, window = resource_analytics.list_resources(
        session, resource_filters, pagination.page, pagination.page_size
    )
    return ResourceListResponse(
        window=window,
        pagination=pagination_out,
        summary=summary,
        items=[_item(row) for row in rows],
    )


@router.get("/{resource_id}", response_model=ResourceDetailResponse)
def get_resource(session: SessionDep, resource_id: str) -> ResourceDetailResponse:
    detail = resource_analytics.get_resource_detail(session, resource_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} was not found.")
    resource = detail["resource"]
    return ResourceDetailResponse(
        resource_id=resource.resource_id,
        resource_name=resource.resource_name,
        resource_type=resource.resource_type,
        service_id=resource.service_id,
        service_name=detail["service_name"],
        project_id=resource.project_id,
        project_name=detail["project_name"],
        region=resource.region,
        zone=resource.zone,
        status=resource.status,
        environment=resource.environment,
        machine_type=resource.machine_type,
        owner=resource.owner,
        team=resource.team,
        application=resource.application,
        labels=resource.labels or {},
        created_at=resource.created_at,
        last_seen=resource.last_seen,
        window=detail["window"],
        monthly_cost=detail["monthly_cost"],
        monthly_credits=detail["monthly_credits"],
        monthly_net_cost=detail["monthly_net_cost"],
        total_cost=detail["total_cost"],
        total_net_cost=detail["total_net_cost"],
        cpu_utilization=detail["cpu_utilization"],
        memory_utilization=detail["memory_utilization"],
        cost_history=detail["cost_history"],
        utilization=detail["utilization"],
    )
