"""Ingest a provider snapshot into PostgreSQL.

Demo-data seeding is a full replace of the fact tables (cost_records,
resource_usage) inside one transaction; dimension rows (services, projects,
resources) are upserted. The caller decides when replacement is allowed —
`costlab.seed` only replaces in demo mode with an explicit `--force`.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from costlab.db.models import CostRecord, Project, Resource, ResourceUsage, Service
from costlab.schemas.input import BillingSnapshot, UsageRecordInput


@dataclass(frozen=True)
class IngestResult:
    source: str
    services: int
    projects: int
    resources: int
    cost_records: int
    usage_records: int


def _validate_references(snapshot: BillingSnapshot, usage_records: list[UsageRecordInput]) -> None:
    """Fail with a precise message before the database raises an opaque FK error."""
    service_ids = {s.service_id for s in snapshot.services}
    project_ids = {p.project_id for p in snapshot.projects}
    resource_ids = {r.resource_id for r in snapshot.resources}

    for resource in snapshot.resources:
        if resource.service_id not in service_ids:
            raise ValueError(
                f"Resource {resource.resource_id} references "
                f"unknown service {resource.service_id!r}"
            )
        if resource.project_id not in project_ids:
            raise ValueError(
                f"Resource {resource.resource_id} references "
                f"unknown project {resource.project_id!r}"
            )
    for row in snapshot.cost_records:
        if row.service_id not in service_ids:
            raise ValueError(
                f"Cost row {row.usage_date}/{row.resource_id} references "
                f"unknown service {row.service_id!r}"
            )
        if row.project_id not in project_ids:
            raise ValueError(
                f"Cost row {row.usage_date}/{row.resource_id} references "
                f"unknown project {row.project_id!r}"
            )
        if row.resource_id not in resource_ids:
            raise ValueError(
                f"Cost row {row.usage_date} references unknown resource {row.resource_id!r}"
            )
    for usage_row in usage_records:
        if usage_row.resource_id not in resource_ids:
            raise ValueError(
                f"Usage row {usage_row.usage_date} references "
                f"unknown resource {usage_row.resource_id!r}"
            )


def ingest_snapshot(
    session: Session,
    snapshot: BillingSnapshot,
    usage_records: list[UsageRecordInput],
    *,
    replace_facts: bool,
) -> IngestResult:
    _validate_references(snapshot, usage_records)

    if replace_facts:
        session.execute(delete(CostRecord))
        session.execute(delete(ResourceUsage))

    for service in snapshot.services:
        session.merge(
            Service(
                id=service.service_id, display_name=service.display_name, category=service.category
            )
        )
    for project in snapshot.projects:
        session.merge(
            Project(
                id=project.project_id,
                display_name=project.display_name,
                environment=project.environment,
                labels=project.labels,
            )
        )
    # No ORM relationships are declared between these mappers, so the unit of
    # work does not derive insert order from table FKs — flush each level
    # explicitly: dimensions first, then resources, then facts.
    session.flush()

    for resource in snapshot.resources:
        session.merge(
            Resource(
                resource_id=resource.resource_id,
                resource_name=resource.resource_name,
                resource_type=resource.type,
                service_id=resource.service_id,
                project_id=resource.project_id,
                region=resource.region,
                zone=resource.zone,
                status=resource.status,
                environment=resource.environment,
                machine_type=resource.machine_type,
                owner=resource.owner,
                team=resource.team,
                application=resource.application,
                labels=resource.labels,
                created_at=resource.created_at,
                last_seen=resource.last_seen,
            )
        )
    session.flush()  # resources must exist before fact FKs resolve

    session.add_all(
        CostRecord(
            usage_date=row.usage_date,
            project_id=row.project_id,
            service_id=row.service_id,
            resource_id=row.resource_id,
            sku=row.sku,
            region=row.region,
            environment=row.environment,
            usage_amount=str(row.usage_amount),
            usage_unit=row.usage_unit,
            cost=str(row.cost),
            credits=str(row.credits),
            net_cost=str(row.net_cost),
            currency=row.currency,
            labels=row.labels,
        )
        for row in snapshot.cost_records
    )
    session.add_all(
        ResourceUsage(
            resource_id=row.resource_id,
            usage_date=row.usage_date,
            cpu_utilization=_opt_str(row.cpu_utilization),
            memory_utilization=_opt_str(row.memory_utilization),
            disk_utilization=_opt_str(row.disk_utilization),
            network_in_mb=_opt_str(row.network_in_mb),
            network_out_mb=_opt_str(row.network_out_mb),
            request_count=row.request_count,
            latency_ms=_opt_str(row.latency_ms),
            error_rate_pct=_opt_str(row.error_rate_pct),
        )
        for row in usage_records
    )
    return IngestResult(
        source=snapshot.source,
        services=len(snapshot.services),
        projects=len(snapshot.projects),
        resources=len(snapshot.resources),
        cost_records=len(snapshot.cost_records),
        usage_records=len(usage_records),
    )


def _opt_str(value: float | int | None) -> str | None:
    """Numeric columns receive values as strings to keep exact Decimal semantics."""
    return None if value is None else str(value)


def cost_record_count(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(CostRecord)).scalar_one())
