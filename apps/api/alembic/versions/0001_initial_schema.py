"""initial schema: projects, services, resources, cost_records, resource_usage

Revision ID: 0001
Revises:
Create Date: 2026-09-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_environment"), "projects", ["environment"], unique=False)
    op.create_table(
        "resources",
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("resource_name", sa.String(length=256), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("service_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("zone", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("machine_type", sa.String(length=64), nullable=True),
        sa.Column("owner", sa.String(length=64), nullable=True),
        sa.Column("team", sa.String(length=64), nullable=True),
        sa.Column("application", sa.String(length=64), nullable=True),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("resource_id"),
    )
    op.create_index(
        op.f("ix_resources_resource_type"), "resources", ["resource_type"], unique=False
    )
    op.create_index(op.f("ix_resources_service_id"), "resources", ["service_id"], unique=False)
    op.create_index(op.f("ix_resources_project_id"), "resources", ["project_id"], unique=False)
    op.create_index(op.f("ix_resources_region"), "resources", ["region"], unique=False)
    op.create_index(op.f("ix_resources_environment"), "resources", ["environment"], unique=False)
    op.create_table(
        "cost_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("service_id", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("sku", sa.String(length=256), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("usage_amount", sa.Numeric(16, 6), nullable=False),
        sa.Column("usage_unit", sa.String(length=32), nullable=False),
        sa.Column("cost", sa.Numeric(14, 6), nullable=False),
        sa.Column("credits", sa.Numeric(14, 6), nullable=False),
        sa.Column("net_cost", sa.Numeric(14, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.resource_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cost_records_usage_date"), "cost_records", ["usage_date"], unique=False
    )
    op.create_index(
        op.f("ix_cost_records_project_id"), "cost_records", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_cost_records_service_id"), "cost_records", ["service_id"], unique=False
    )
    op.create_index(
        op.f("ix_cost_records_resource_id"), "cost_records", ["resource_id"], unique=False
    )
    op.create_index(op.f("ix_cost_records_region"), "cost_records", ["region"], unique=False)
    op.create_index(
        op.f("ix_cost_records_environment"), "cost_records", ["environment"], unique=False
    )
    op.create_index(
        "ix_cost_records_date_project", "cost_records", ["usage_date", "project_id"], unique=False
    )
    op.create_index(
        "ix_cost_records_date_service", "cost_records", ["usage_date", "service_id"], unique=False
    )
    op.create_index(
        "ix_cost_records_date_environment",
        "cost_records",
        ["usage_date", "environment"],
        unique=False,
    )
    op.create_table(
        "resource_usage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("cpu_utilization", sa.Numeric(6, 3), nullable=True),
        sa.Column("memory_utilization", sa.Numeric(6, 3), nullable=True),
        sa.Column("disk_utilization", sa.Numeric(6, 3), nullable=True),
        sa.Column("network_in_mb", sa.Numeric(14, 4), nullable=True),
        sa.Column("network_out_mb", sa.Numeric(14, 4), nullable=True),
        sa.Column("request_count", sa.BigInteger(), nullable=True),
        sa.Column("latency_ms", sa.Numeric(12, 3), nullable=True),
        sa.Column("error_rate_pct", sa.Numeric(6, 3), nullable=True),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.resource_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_id", "usage_date", name="uq_resource_usage_resource_date"),
    )
    op.create_index(
        op.f("ix_resource_usage_resource_id"), "resource_usage", ["resource_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resource_usage_resource_id"), table_name="resource_usage")
    op.drop_table("resource_usage")
    op.drop_index("ix_cost_records_date_environment", table_name="cost_records")
    op.drop_index("ix_cost_records_date_service", table_name="cost_records")
    op.drop_index("ix_cost_records_date_project", table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_environment"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_region"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_resource_id"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_service_id"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_project_id"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_usage_date"), table_name="cost_records")
    op.drop_table("cost_records")
    op.drop_index(op.f("ix_resources_environment"), table_name="resources")
    op.drop_index(op.f("ix_resources_region"), table_name="resources")
    op.drop_index(op.f("ix_resources_project_id"), table_name="resources")
    op.drop_index(op.f("ix_resources_service_id"), table_name="resources")
    op.drop_index(op.f("ix_resources_resource_type"), table_name="resources")
    op.drop_table("resources")
    op.drop_index(op.f("ix_projects_environment"), table_name="projects")
    op.drop_table("projects")
    op.drop_table("services")
