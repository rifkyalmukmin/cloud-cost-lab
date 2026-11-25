"""Persist recommendation lifecycle when a database URL is configured.

Demo mode keeps the in-memory store. Docker sets PERSIST_LIFECYCLE=true and
this module writes that same store to PostgreSQL after Alembic upgrade.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    AuditLogRow,
    CostDailyAggregate,
    Project,
    RecommendationStateRow,
    Resource,
    Service,
)
from app.services.mock_data import PROJECTS, RESOURCE_LABELS, RESOURCES, SERVICES

API_ROOT = Path(__file__).resolve().parents[1]


def upgrade_database(database_url: str) -> None:
    """Apply Alembic migrations to the given database."""
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _enable_sqlite_foreign_keys(engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _money(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def seed_reference_data(engine) -> None:
    """Insert projects, services, and resources so lifecycle foreign keys resolve."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        for project in PROJECTS:
            if session.query(Project).filter_by(project_id=project["project_id"]).one_or_none():
                continue
            session.add(
                Project(
                    project_id=project["project_id"],
                    project_name=project["project_name"],
                    environment=project["environment"],
                    team=project["team"],
                    owner=project["owner"],
                )
            )
        for service in SERVICES:
            if session.query(Service).filter_by(service_id=service["service_id"]).one_or_none():
                continue
            session.add(
                Service(
                    service_id=service["service_id"],
                    service_name=service["service_name"],
                    category=service["category"],
                )
            )
        session.flush()
        for resource in RESOURCES:
            if session.query(Resource).filter_by(resource_id=resource["resource_id"]).one_or_none():
                continue
            session.add(
                Resource(
                    resource_id=resource["resource_id"],
                    resource_name=resource["resource_name"],
                    resource_type=resource["resource_type"],
                    service_id=resource["service_id"],
                    project_id=resource["project_id"],
                    region=resource["region"],
                    zone=resource["zone"],
                    environment=resource["environment"],
                    status=resource["status"],
                    owner=resource["owner"],
                    team=resource["team"],
                    application=resource["application"],
                    labels=json.dumps(RESOURCE_LABELS.get(resource["resource_id"], {})),
                )
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class LifecyclePersister:
    """Write-through copy of the in-memory lifecycle store."""

    def __init__(self, engine):
        self.engine = engine
        self._session_factory = sessionmaker(bind=engine)

    def load_or_store_seed(self, service) -> None:
        session = self._session_factory()
        try:
            rows = session.query(RecommendationStateRow).all()
            if not rows:
                if service._recommendations_state:
                    self._write(session, service)
                    session.commit()
                return

            service._recommendations_state = {
                row.recommendation_id: json.loads(row.payload) for row in rows
            }
            audit_rows = (
                session.query(AuditLogRow).order_by(AuditLogRow.id.asc()).all()
            )
            service._audit_log = [_audit_to_dict(row) for row in audit_rows]
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def sync(self, service) -> None:
        session = self._session_factory()
        try:
            self._write(session, service)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _write(self, session, service) -> None:
        session.query(AuditLogRow).delete()
        session.query(RecommendationStateRow).delete()
        session.flush()
        for rec_id, rec in service._recommendations_state.items():
            session.add(
                RecommendationStateRow(
                    recommendation_id=rec_id,
                    resource_id=rec["resource_id"],
                    status=rec["status"],
                    potential_savings=_money(rec.get("potential_savings", 0)) or Decimal("0"),
                    current_cost=_money(rec.get("current_cost", 0)) or Decimal("0"),
                    cost_before=_money(rec.get("cost_before")),
                    cost_after=_money(rec.get("cost_after")),
                    realized_savings=_money(rec.get("realized_savings")),
                    approved_by=rec.get("approved_by"),
                    approved_at=rec.get("approved_at"),
                    implemented_by=rec.get("implemented_by"),
                    implemented_at=rec.get("implemented_at"),
                    verified_at=rec.get("verified_at"),
                    rejected_by=rec.get("rejected_by"),
                    rejected_at=rec.get("rejected_at"),
                    rejection_reason=rec.get("rejection_reason"),
                    payload=json.dumps(rec),
                )
            )
        session.flush()
        for entry in service._audit_log:
            session.add(
                AuditLogRow(
                    recommendation_id=entry["recommendation_id"],
                    timestamp=entry["timestamp"],
                    action=entry["action"],
                    actor=entry["actor"],
                    reason=entry.get("reason"),
                    cost_before=_money(entry.get("cost_before")),
                    cost_after=_money(entry.get("cost_after")),
                    realized_savings=_money(entry.get("realized_savings")),
                )
            )


def _audit_to_dict(row: AuditLogRow) -> dict:
    entry = {
        "timestamp": row.timestamp,
        "action": row.action,
        "recommendation_id": row.recommendation_id,
        "actor": row.actor,
    }
    if row.reason is not None:
        entry["reason"] = row.reason
    if row.cost_before is not None:
        entry["cost_before"] = float(row.cost_before)
    if row.cost_after is not None:
        entry["cost_after"] = float(row.cost_after)
    if row.realized_savings is not None:
        entry["realized_savings"] = float(row.realized_savings)
    return entry


def sync_cost_aggregates(engine, records: list[dict]) -> list[dict]:
    """Replace daily cost aggregates and return the rows the explorer should read."""
    grouped: dict[tuple, dict] = {}
    for record in records:
        project_id = record.get("project_id")
        service_id = record.get("service_id")
        if not project_id or not service_id:
            continue
        usage_date = record["usage_date"]
        if isinstance(usage_date, str):
            usage_date = date.fromisoformat(usage_date[:10])
        environment = record.get("environment") or "UNALLOCATED"
        key = (usage_date, project_id, service_id, environment)
        bucket = grouped.setdefault(
            key,
            {
                "project_name": record.get("project_name") or project_id,
                "service_name": record.get("service_name") or service_id,
                "cost": Decimal("0"),
                "net_cost": Decimal("0"),
                "currency": record.get("currency") or "USD",
            },
        )
        bucket["cost"] += Decimal(str(record.get("cost", 0)))
        bucket["net_cost"] += Decimal(str(record.get("net_cost", 0)))

    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    stored: list[dict] = []
    try:
        session.query(CostDailyAggregate).delete()
        for (usage_date, project_id, service_id, environment), bucket in grouped.items():
            cost = bucket["cost"].quantize(Decimal("0.0001"))
            net_cost = bucket["net_cost"].quantize(Decimal("0.0001"))
            session.add(
                CostDailyAggregate(
                    usage_date=usage_date,
                    project_id=project_id,
                    service_id=service_id,
                    project_name=bucket["project_name"],
                    service_name=bucket["service_name"],
                    environment=environment,
                    cost=cost,
                    net_cost=net_cost,
                    currency=bucket["currency"],
                )
            )
            stored.append(
                {
                    "usage_date": usage_date,
                    "project_id": project_id,
                    "service_id": service_id,
                    "project_name": bucket["project_name"],
                    "service_name": bucket["service_name"],
                    "environment": environment,
                    "cost": float(cost),
                    "net_cost": float(net_cost),
                    "currency": bucket["currency"],
                }
            )
        session.commit()
        return stored
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def bind_lifecycle(service, database_url: str) -> None:
    """Upgrade the schema, seed reference rows, and attach the persister."""
    upgrade_database(database_url)
    engine = create_engine(database_url, pool_pre_ping=True)
    if database_url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    seed_reference_data(engine)
    persister = LifecyclePersister(engine)
    persister.load_or_store_seed(service)
    service._persister = persister

    from app.services.cost_service import cost_service

    cost_service.use_stored_aggregates(sync_cost_aggregates(engine, cost_service.records))
