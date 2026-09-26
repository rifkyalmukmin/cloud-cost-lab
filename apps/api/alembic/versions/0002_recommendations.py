"""recommendations table (Phase 5)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("service_id", sa.String(length=64), nullable=True),
        sa.Column("scope_key", sa.String(length=192), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("problem", sa.String(length=512), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendation", sa.String(length=1024), nullable=False),
        sa.Column("current_cost", sa.Numeric(14, 6), nullable=False),
        sa.Column("potential_cost", sa.Numeric(14, 6), nullable=False),
        sa.Column("potential_savings", sa.Numeric(14, 6), nullable=False),
        sa.Column("savings_percentage", sa.Numeric(6, 2), nullable=False),
        sa.Column("risk", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("effort", sa.String(length=16), nullable=False),
        sa.Column("priority_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.resource_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "scope_key", name="uq_recommendations_rule_scope"),
    )
    op.create_index(op.f("ix_recommendations_rule_id"), "recommendations", ["rule_id"])
    op.create_index(op.f("ix_recommendations_resource_id"), "recommendations", ["resource_id"])
    op.create_index(op.f("ix_recommendations_project_id"), "recommendations", ["project_id"])
    op.create_index(op.f("ix_recommendations_status"), "recommendations", ["status"])
    op.create_index(
        "ix_recommendations_status_priority", "recommendations", ["status", "priority_score"]
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_status_priority", table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_status"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_project_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_resource_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_rule_id"), table_name="recommendations")
    op.drop_table("recommendations")
