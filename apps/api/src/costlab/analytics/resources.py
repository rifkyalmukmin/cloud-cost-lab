"""Resource inventory queries (Phase 3).

Monthly cost per resource = trailing 30 days of cost data, anchored to the
data itself (max usage_date - 29 days .. max usage_date), never the wall clock
(same freshness philosophy as analytics.cost.resolve_period).
CPU/Memory = latest utilization sample per resource.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from costlab.analytics.cost import _money
from costlab.db.models import CostRecord, Project, Resource, ResourceUsage, Service
from costlab.schemas.cost import PaginationOut
from costlab.schemas.resources import (
    CostHistoryPoint,
    ResourceCostSummary,
    ResourceFilters,
    ResourceWindow,
    UtilizationPoint,
)

WINDOW_DAYS = 30


@dataclass(frozen=True)
class ResourceRow:
    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    service_name: str
    project_id: str
    project_name: str
    region: str
    zone: str | None
    status: str
    environment: str
    machine_type: str | None
    owner: str | None
    team: str | None
    application: str | None
    labels: dict
    created_at: Any | None
    last_seen: Any | None
    monthly_cost: float | None
    monthly_credits: float | None
    monthly_net_cost: float | None
    cpu_utilization: float | None
    memory_utilization: float | None


def get_window(session: Session) -> ResourceWindow | None:
    """Trailing 30-day window anchored to the newest cost record."""
    max_date = session.execute(select(func.max(CostRecord.usage_date))).scalar_one()
    if max_date is None:
        return None
    return ResourceWindow(start=max_date - timedelta(days=WINDOW_DAYS - 1), end=max_date)


def apply_filters(stmt: Select, filters: ResourceFilters) -> Select:
    if filters.project_id:
        stmt = stmt.where(Resource.project_id == filters.project_id)
    if filters.service:
        stmt = stmt.where(Resource.service_id == filters.service)
    if filters.region:
        stmt = stmt.where(Resource.region == filters.region)
    if filters.environment:
        stmt = stmt.where(Resource.environment == filters.environment)
    if filters.status:
        stmt = stmt.where(Resource.status == filters.status)
    if filters.owner:
        stmt = stmt.where(Resource.owner == filters.owner)
    if filters.team:
        stmt = stmt.where(Resource.team == filters.team)
    if filters.unallocated:
        # Missing attribution — never guessed, surfaced as UNALLOCATED.
        stmt = stmt.where(or_(Resource.owner.is_(None), Resource.team.is_(None)))
    return stmt


def _monthly_cost_subquery(window: ResourceWindow):
    return (
        select(
            CostRecord.resource_id,
            func.sum(CostRecord.cost).label("monthly_cost"),
            func.sum(CostRecord.credits).label("monthly_credits"),
            func.sum(CostRecord.net_cost).label("monthly_net_cost"),
        )
        .where(CostRecord.usage_date >= window.start, CostRecord.usage_date <= window.end)
        .group_by(CostRecord.resource_id)
        .subquery()
    )


def _latest_usage_subquery():
    latest = (
        select(
            ResourceUsage.resource_id,
            func.max(ResourceUsage.usage_date).label("max_date"),
        )
        .group_by(ResourceUsage.resource_id)
        .subquery()
    )
    return (
        select(
            ResourceUsage.resource_id,
            ResourceUsage.cpu_utilization,
            ResourceUsage.memory_utilization,
        )
        .join(
            latest,
            and_(
                ResourceUsage.resource_id == latest.c.resource_id,
                ResourceUsage.usage_date == latest.c.max_date,
            ),
        )
        .subquery()
    )


def _base_query(filters: ResourceFilters, window: ResourceWindow, cost_sub) -> Select:
    usage_sub = _latest_usage_subquery()
    stmt = (
        select(
            Resource,
            Service.display_name,
            Project.display_name,
            cost_sub.c.monthly_cost,
            cost_sub.c.monthly_credits,
            cost_sub.c.monthly_net_cost,
            usage_sub.c.cpu_utilization,
            usage_sub.c.memory_utilization,
        )
        .join(Service, Resource.service_id == Service.id)
        .join(Project, Resource.project_id == Project.id)
        .outerjoin(cost_sub, Resource.resource_id == cost_sub.c.resource_id)
        .outerjoin(usage_sub, Resource.resource_id == usage_sub.c.resource_id)
    )
    return apply_filters(stmt, filters)


def resource_cost_summary(
    session: Session,
    filters: ResourceFilters,
    window: ResourceWindow,
) -> ResourceCostSummary:
    """Totals over the window for the FULL filtered set (not just one page)."""
    cost_sub = _monthly_cost_subquery(window)
    stmt = apply_filters(
        select(
            func.coalesce(func.sum(cost_sub.c.monthly_cost), 0),
            func.coalesce(func.sum(cost_sub.c.monthly_credits), 0),
            func.coalesce(func.sum(cost_sub.c.monthly_net_cost), 0),
        )
        .select_from(Resource)
        .join(cost_sub, Resource.resource_id == cost_sub.c.resource_id),
        filters,
    )
    cost, credits, net_cost = session.execute(stmt).one()
    return ResourceCostSummary(
        monthly_cost=_money(cost),
        monthly_credits=_money(credits),
        monthly_net_cost=_money(net_cost),
    )


def list_resources(
    session: Session,
    filters: ResourceFilters,
    page: int,
    page_size: int,
) -> tuple[list[ResourceRow], PaginationOut, ResourceCostSummary | None, ResourceWindow | None]:
    window = get_window(session)
    if window is None:
        empty = PaginationOut(page=page, page_size=page_size, total_items=0, total_pages=0)
        return [], empty, None, None

    total = int(
        session.execute(
            apply_filters(select(func.count()).select_from(Resource), filters)
        ).scalar_one()
    )

    cost_sub = _monthly_cost_subquery(window)
    ordered = (
        _base_query(filters, window, cost_sub)
        .order_by(cost_sub.c.monthly_cost.desc().nullslast(), Resource.resource_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows: list[ResourceRow] = []
    for row in session.execute(ordered):
        resource = row[0]
        rows.append(
            ResourceRow(
                resource_id=resource.resource_id,
                resource_name=resource.resource_name,
                resource_type=resource.resource_type,
                service_id=resource.service_id,
                service_name=row[1],
                project_id=resource.project_id,
                project_name=row[2],
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
                monthly_cost=_money(row[3]) if row[3] is not None else None,
                monthly_credits=_money(row[4]) if row[4] is not None else None,
                monthly_net_cost=_money(row[5]) if row[5] is not None else None,
                cpu_utilization=round(float(row[6]), 2) if row[6] is not None else None,
                memory_utilization=round(float(row[7]), 2) if row[7] is not None else None,
            )
        )

    summary = resource_cost_summary(session, filters, window)
    pagination = PaginationOut(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )
    return rows, pagination, summary, window


def get_resource_detail(session: Session, resource_id: str) -> dict | None:
    """Full detail for one resource, or None when the id is unknown."""
    window = get_window(session)
    resource = session.get(Resource, resource_id)
    if resource is None:
        return None

    service = session.get(Service, resource.service_id)
    project = session.get(Project, resource.project_id)

    if window is not None:
        monthly_row = session.execute(
            select(
                func.coalesce(func.sum(CostRecord.cost), 0),
                func.coalesce(func.sum(CostRecord.credits), 0),
                func.coalesce(func.sum(CostRecord.net_cost), 0),
            ).where(
                CostRecord.resource_id == resource_id,
                CostRecord.usage_date >= window.start,
                CostRecord.usage_date <= window.end,
            )
        ).one()
        monthly = (monthly_row[0], monthly_row[1], monthly_row[2])
    else:
        monthly = (Decimal(0), Decimal(0), Decimal(0))

    total = session.execute(
        select(
            func.coalesce(func.sum(CostRecord.cost), 0),
            func.coalesce(func.sum(CostRecord.net_cost), 0),
        ).where(CostRecord.resource_id == resource_id)
    ).one()

    history_rows = (
        session.execute(
            select(CostRecord)
            .where(CostRecord.resource_id == resource_id)
            .order_by(CostRecord.usage_date.asc())
        )
        .scalars()
        .all()
    )
    usage_rows = (
        session.execute(
            select(ResourceUsage)
            .where(ResourceUsage.resource_id == resource_id)
            .order_by(ResourceUsage.usage_date.asc())
        )
        .scalars()
        .all()
    )
    latest_usage = usage_rows[-1] if usage_rows else None

    def _round(value: Decimal | None, digits: int = 2) -> float | None:
        return round(float(value), digits) if value is not None else None

    return {
        "resource": resource,
        "service_name": service.display_name if service else resource.service_id,
        "project_name": project.display_name if project else resource.project_id,
        "window": window,
        "monthly_cost": _money(monthly[0]) if window else None,
        "monthly_credits": _money(monthly[1]) if window else None,
        "monthly_net_cost": _money(monthly[2]) if window else None,
        "total_cost": _money(total[0]),
        "total_net_cost": _money(total[1]),
        "cpu_utilization": _round(latest_usage.cpu_utilization) if latest_usage else None,
        "memory_utilization": _round(latest_usage.memory_utilization) if latest_usage else None,
        "cost_history": [
            CostHistoryPoint(
                date=row.usage_date,
                cost=_money(row.cost),
                credits=_money(row.credits),
                net_cost=_money(row.net_cost),
            )
            for row in history_rows
        ],
        "utilization": [
            UtilizationPoint(
                date=row.usage_date,
                cpu_utilization=_round(row.cpu_utilization),
                memory_utilization=_round(row.memory_utilization),
                disk_utilization=_round(row.disk_utilization),
                network_in_mb=round(float(row.network_in_mb), 2)
                if row.network_in_mb is not None
                else None,
                network_out_mb=round(float(row.network_out_mb), 2)
                if row.network_out_mb is not None
                else None,
                request_count=row.request_count,
                error_rate_pct=round(float(row.error_rate_pct), 3)
                if row.error_rate_pct is not None
                else None,
            )
            for row in usage_rows
        ],
    }
