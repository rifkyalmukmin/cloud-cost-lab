"""Initial schema: numeric money, foreign keys, and lookup indexes."""

import sqlalchemy as sa
from alembic import op

revision = "20261125_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.String(length=100), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("team", sa.String(length=100)),
        sa.Column("owner", sa.String(length=100)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("project_id", name="uq_projects_project_id"),
    )
    op.create_index("ix_projects_project_id", "projects", ["project_id"])
    op.create_index("ix_projects_environment", "projects", ["environment"])

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_id", sa.String(length=100), nullable=False),
        sa.Column("service_name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100)),
        sa.UniqueConstraint("service_id", name="uq_services_service_id"),
    )
    op.create_index("ix_services_service_id", "services", ["service_id"])

    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.String(length=200), nullable=False),
        sa.Column("resource_name", sa.String(length=200), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("service_id", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100)),
        sa.Column("zone", sa.String(length=100)),
        sa.Column("environment", sa.String(length=50)),
        sa.Column("status", sa.String(length=50)),
        sa.Column("owner", sa.String(length=100)),
        sa.Column("team", sa.String(length=100)),
        sa.Column("application", sa.String(length=100)),
        sa.Column("labels", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_seen", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"], name="fk_resources_service_id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], name="fk_resources_project_id"),
        sa.UniqueConstraint("resource_id", name="uq_resources_resource_id"),
    )
    op.create_index("ix_resources_resource_id", "resources", ["resource_id"])
    op.create_index("ix_resources_service_id", "resources", ["service_id"])
    op.create_index("ix_resources_project_id", "resources", ["project_id"])
    op.create_index("ix_resources_environment", "resources", ["environment"])

    op.create_table(
        "resource_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.String(length=200), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("cpu_utilization", sa.Float()),
        sa.Column("memory_utilization", sa.Float()),
        sa.Column("disk_utilization", sa.Float()),
        sa.Column("network_in", sa.Float()),
        sa.Column("network_out", sa.Float()),
        sa.Column("request_count", sa.Integer()),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.resource_id"], name="fk_resource_usage_resource_id"),
    )
    op.create_index("ix_resource_usage_resource_id", "resource_usage", ["resource_id"])
    op.create_index("ix_resource_usage_timestamp", "resource_usage", ["timestamp"])

    op.create_table(
        "cost_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.String(length=100), nullable=False),
        sa.Column("project_name", sa.String(length=200)),
        sa.Column("service_id", sa.String(length=100), nullable=False),
        sa.Column("service_name", sa.String(length=200)),
        sa.Column("sku", sa.String(length=200)),
        sa.Column("region", sa.String(length=100)),
        sa.Column("resource_id", sa.String(length=200)),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("usage_amount", sa.Numeric(18, 6)),
        sa.Column("usage_unit", sa.String(length=50)),
        sa.Column("cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("currency", sa.String(length=10)),
        sa.Column("credits", sa.Numeric(14, 4)),
        sa.Column("net_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("environment", sa.String(length=50)),
        sa.Column("team", sa.String(length=100)),
        sa.Column("application", sa.String(length=100)),
        sa.Column("labels", sa.Text()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], name="fk_cost_records_project_id"),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"], name="fk_cost_records_service_id"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.resource_id"], name="fk_cost_records_resource_id"),
        sa.UniqueConstraint(
            "project_id",
            "service_id",
            "sku",
            "resource_id",
            "usage_date",
            name="uq_cost_records_line",
        ),
    )
    op.create_index("ix_cost_records_project_id", "cost_records", ["project_id"])
    op.create_index("ix_cost_records_service_id", "cost_records", ["service_id"])
    op.create_index("ix_cost_records_resource_id", "cost_records", ["resource_id"])
    op.create_index("ix_cost_records_usage_date", "cost_records", ["usage_date"])
    op.create_index("ix_cost_records_environment", "cost_records", ["environment"])

    op.create_table(
        "recommendation_states",
        sa.Column("recommendation_id", sa.String(length=64), primary_key=True),
        sa.Column("resource_id", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("potential_savings", sa.Numeric(14, 4), nullable=False),
        sa.Column("current_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("cost_before", sa.Numeric(14, 4)),
        sa.Column("cost_after", sa.Numeric(14, 4)),
        sa.Column("realized_savings", sa.Numeric(14, 4)),
        sa.Column("approved_by", sa.String(length=100)),
        sa.Column("approved_at", sa.String(length=40)),
        sa.Column("implemented_by", sa.String(length=100)),
        sa.Column("implemented_at", sa.String(length=40)),
        sa.Column("verified_at", sa.String(length=40)),
        sa.Column("rejected_by", sa.String(length=100)),
        sa.Column("rejected_at", sa.String(length=40)),
        sa.Column("rejection_reason", sa.String(length=500)),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.resource_id"], name="fk_recommendation_states_resource_id"),
    )
    op.create_index("ix_recommendation_states_resource_id", "recommendation_states", ["resource_id"])
    op.create_index("ix_recommendation_states_status", "recommendation_states", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recommendation_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.String(length=500)),
        sa.Column("cost_before", sa.Numeric(14, 4)),
        sa.Column("cost_after", sa.Numeric(14, 4)),
        sa.Column("realized_savings", sa.Numeric(14, 4)),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendation_states.recommendation_id"],
            name="fk_audit_logs_recommendation_id",
        ),
    )
    op.create_index("ix_audit_logs_recommendation_id", "audit_logs", ["recommendation_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("recommendation_states")
    op.drop_table("cost_records")
    op.drop_table("resource_usage")
    op.drop_table("resources")
    op.drop_table("services")
    op.drop_table("projects")
