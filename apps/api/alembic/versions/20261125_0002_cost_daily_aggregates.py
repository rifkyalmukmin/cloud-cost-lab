"""Daily cost aggregates with numeric money, foreign keys, and indexes."""

import sqlalchemy as sa
from alembic import op

revision = "20261125_0002"
down_revision = "20261125_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_daily_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.String(length=100), nullable=False),
        sa.Column("service_id", sa.String(length=100), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("service_name", sa.String(length=200), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("net_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], name="fk_cost_daily_aggregates_project_id"),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"], name="fk_cost_daily_aggregates_service_id"),
        sa.UniqueConstraint(
            "usage_date",
            "project_id",
            "service_id",
            "environment",
            name="uq_cost_daily_aggregate",
        ),
    )
    op.create_index("ix_cost_daily_aggregates_usage_date", "cost_daily_aggregates", ["usage_date"])
    op.create_index("ix_cost_daily_aggregates_project_id", "cost_daily_aggregates", ["project_id"])
    op.create_index("ix_cost_daily_aggregates_service_id", "cost_daily_aggregates", ["service_id"])
    op.create_index("ix_cost_daily_aggregates_environment", "cost_daily_aggregates", ["environment"])


def downgrade() -> None:
    op.drop_index("ix_cost_daily_aggregates_environment", table_name="cost_daily_aggregates")
    op.drop_index("ix_cost_daily_aggregates_service_id", table_name="cost_daily_aggregates")
    op.drop_index("ix_cost_daily_aggregates_project_id", table_name="cost_daily_aggregates")
    op.drop_index("ix_cost_daily_aggregates_usage_date", table_name="cost_daily_aggregates")
    op.drop_table("cost_daily_aggregates")
