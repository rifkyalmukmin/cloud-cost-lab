"""Cost aggregation queries (Phase 1: daily / weekly / monthly + breakdowns).

Rules (CLAUDE.md §9, §14):
- aggregation happens in SQL, never by pulling rows into Python;
- money is summed as exact Numeric/Decimal and converted to rounded floats
  only at the response boundary;
- every query is filterable and bounded; no unbounded result sets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import DateTime, Select, cast, func, select
from sqlalchemy.orm import Session

from costlab.db.models import CostRecord, Project, Service
from costlab.schemas.cost import CostFilters

Granularity = Literal["day", "week", "month"]


@dataclass(frozen=True)
class Bounds:
    min_date: date
    max_date: date


@dataclass(frozen=True)
class Money:
    cost: float
    credits: float
    net_cost: float


@dataclass(frozen=True)
class TrendRow:
    period: date
    cost: float
    credits: float
    net_cost: float


@dataclass(frozen=True)
class BreakdownRow:
    key: str
    label: str
    cost: float
    credits: float
    net_cost: float


@dataclass(frozen=True)
class CostRecordRow:
    usage_date: date
    project_id: str
    service: str
    service_name: str
    resource_id: str | None
    sku: str
    region: str
    environment: str
    usage_amount: float
    usage_unit: str
    cost: float
    credits: float
    net_cost: float
    currency: str
    labels: dict


def _money(value: Decimal | int | float | None) -> float:
    return round(float(value or 0), 4)


def apply_filters(stmt: Select, filters: CostFilters) -> Select:
    if filters.start_date is not None:
        stmt = stmt.where(CostRecord.usage_date >= filters.start_date)
    if filters.end_date is not None:
        stmt = stmt.where(CostRecord.usage_date <= filters.end_date)
    if filters.project_id:
        stmt = stmt.where(CostRecord.project_id == filters.project_id)
    if filters.service:
        stmt = stmt.where(CostRecord.service_id == filters.service)
    if filters.environment:
        stmt = stmt.where(CostRecord.environment == filters.environment)
    if filters.region:
        stmt = stmt.where(CostRecord.region == filters.region)
    if filters.resource_id:
        stmt = stmt.where(CostRecord.resource_id == filters.resource_id)
    return stmt


def get_bounds(session: Session) -> Bounds | None:
    row = session.execute(
        select(
            func.min(CostRecord.usage_date).label("min_date"),
            func.max(CostRecord.usage_date).label("max_date"),
        )
    ).one()
    if row.min_date is None or row.max_date is None:
        return None
    return Bounds(min_date=row.min_date, max_date=row.max_date)


def resolve_period(session: Session, filters: CostFilters) -> tuple[date, date] | None:
    """Effective reporting period.

    Defaults come from the data itself, not the wall clock: the mock dataset is
    date-anchored (ADR-003), so wall-clock defaults would silently return empty
    reports whenever the data is older than "today - 30 days".
    """
    bounds = get_bounds(session)
    if bounds is None:
        return None
    return (filters.start_date or bounds.min_date, filters.end_date or bounds.max_date)


def cost_summary(session: Session, filters: CostFilters) -> Money:
    stmt = apply_filters(
        select(
            func.coalesce(func.sum(CostRecord.cost), 0),
            func.coalesce(func.sum(CostRecord.credits), 0),
            func.coalesce(func.sum(CostRecord.net_cost), 0),
        ),
        filters,
    )
    cost, credits, net_cost = session.execute(stmt).one()
    return Money(cost=_money(cost), credits=_money(credits), net_cost=_money(net_cost))


def cost_trend(session: Session, filters: CostFilters, granularity: Granularity) -> list[TrendRow]:
    """Cost per time bucket. Weeks are ISO weeks (Monday-start), as in billing exports."""
    bucket = func.date_trunc(granularity, cast(CostRecord.usage_date, DateTime)).label("period")
    stmt = (
        apply_filters(
            select(
                bucket,
                func.sum(CostRecord.cost),
                func.sum(CostRecord.credits),
                func.sum(CostRecord.net_cost),
            ),
            filters,
        )
        .group_by(bucket)
        .order_by(bucket.asc())
    )
    return [
        TrendRow(
            period=row.period.date(),
            cost=_money(row[1]),
            credits=_money(row[2]),
            net_cost=_money(row[3]),
        )
        for row in session.execute(stmt)
    ]


def cost_by_service(session: Session, filters: CostFilters) -> list[BreakdownRow]:
    total_cost = func.sum(CostRecord.cost).label("total_cost")
    stmt = (
        apply_filters(
            select(
                Service.id,
                Service.display_name,
                total_cost,
                func.sum(CostRecord.credits),
                func.sum(CostRecord.net_cost),
            ).join(Service, CostRecord.service_id == Service.id),
            filters,
        )
        .group_by(Service.id, Service.display_name)
        .order_by(total_cost.desc())
    )
    return [
        BreakdownRow(
            key=row[0],
            label=row[1],
            cost=_money(row[2]),
            credits=_money(row[3]),
            net_cost=_money(row[4]),
        )
        for row in session.execute(stmt)
    ]


def cost_by_project(session: Session, filters: CostFilters) -> list[BreakdownRow]:
    total_cost = func.sum(CostRecord.cost).label("total_cost")
    stmt = (
        apply_filters(
            select(
                Project.id,
                Project.display_name,
                total_cost,
                func.sum(CostRecord.credits),
                func.sum(CostRecord.net_cost),
            ).join(Project, CostRecord.project_id == Project.id),
            filters,
        )
        .group_by(Project.id, Project.display_name)
        .order_by(total_cost.desc())
    )
    return [
        BreakdownRow(
            key=row[0],
            label=row[1],
            cost=_money(row[2]),
            credits=_money(row[3]),
            net_cost=_money(row[4]),
        )
        for row in session.execute(stmt)
    ]


def cost_by_environment(session: Session, filters: CostFilters) -> list[BreakdownRow]:
    total_cost = func.sum(CostRecord.cost).label("total_cost")
    stmt = (
        apply_filters(
            select(
                CostRecord.environment,
                total_cost,
                func.sum(CostRecord.credits),
                func.sum(CostRecord.net_cost),
            ),
            filters,
        )
        .group_by(CostRecord.environment)
        .order_by(total_cost.desc())
    )
    return [
        BreakdownRow(
            key=row.environment,
            label=row.environment,
            cost=_money(row.total_cost),
            credits=_money(row[2]),
            net_cost=_money(row[3]),
        )
        for row in session.execute(stmt)
    ]


def list_cost_records(
    session: Session,
    filters: CostFilters,
    page: int,
    page_size: int,
) -> tuple[list[CostRecordRow], int]:
    """Paginated cost records (newest first) with the filtered total count."""
    count_stmt = apply_filters(select(func.count()).select_from(CostRecord), filters)
    total = int(session.execute(count_stmt).scalar_one())

    stmt = apply_filters(
        select(CostRecord, Service.display_name).join(Service, CostRecord.service_id == Service.id),
        filters,
    ).order_by(CostRecord.usage_date.desc(), CostRecord.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = [
        CostRecordRow(
            usage_date=record.usage_date,
            project_id=record.project_id,
            service=record.service_id,
            service_name=service_name,
            resource_id=record.resource_id,
            sku=record.sku,
            region=record.region,
            environment=record.environment,
            usage_amount=_money(record.usage_amount),
            usage_unit=record.usage_unit,
            cost=_money(record.cost),
            credits=_money(record.credits),
            net_cost=_money(record.net_cost),
            currency=record.currency,
            labels=record.labels,
        )
        for record, service_name in session.execute(stmt)
    ]
    return rows, total
