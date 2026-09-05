"""Core data model for Phase 1 (CLAUDE.md §10-11).

Five tables: projects, services, resources, resource_usage, cost_records.
Cost is stored as Numeric (exact Decimal) — never float — so aggregation
does not lose cents. Labels are JSONB because label keys vary per resource.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ENVIRONMENTS = ("development", "staging", "production")


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # GCP-style project id
    display_name: Mapped[str] = mapped_column(String(128))
    environment: Mapped[str] = mapped_column(String(16), index=True)
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # slug, e.g. "compute-engine"
    display_name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))


class Resource(Base):
    __tablename__ = "resources"

    resource_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    resource_name: Mapped[str] = mapped_column(String(256))
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    zone: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16), index=True)
    machine_type: Mapped[str | None] = mapped_column(String(64))
    owner: Mapped[str | None] = mapped_column(String(64))
    team: Mapped[str | None] = mapped_column(String(64))
    application: Mapped[str | None] = mapped_column(String(64))
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CostRecord(Base):
    __tablename__ = "cost_records"
    __table_args__ = (
        Index("ix_cost_records_date_project", "usage_date", "project_id"),
        Index("ix_cost_records_date_service", "usage_date", "service_id"),
        Index("ix_cost_records_date_environment", "usage_date", "environment"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    usage_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), nullable=False, index=True)
    # Nullable: some billing lines are not attributable to a single resource.
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.resource_id"), index=True)
    sku: Mapped[str] = mapped_column(String(256))
    region: Mapped[str] = mapped_column(String(64), index=True)
    environment: Mapped[str] = mapped_column(String(16), index=True)
    usage_amount: Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)
    usage_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    credits: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=0)
    net_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ResourceUsage(Base):
    __tablename__ = "resource_usage"
    __table_args__ = (
        UniqueConstraint("resource_id", "usage_date", name="uq_resource_usage_resource_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("resources.resource_id"), nullable=False, index=True
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Not every resource exposes every metric — nullable by design.
    cpu_utilization: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    memory_utilization: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    disk_utilization: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    network_in_mb: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    network_out_mb: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    request_count: Mapped[int | None] = mapped_column(BigInteger)
    latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    error_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
