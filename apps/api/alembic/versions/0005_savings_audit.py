"""savings lifecycle columns + audit_logs table (Phase 13)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recommendations", sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "recommendations", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "recommendations", sa.Column("actual_cost_after", sa.Numeric(14, 6), nullable=True)
    )
    op.add_column(
        "recommendations", sa.Column("realized_savings", sa.Numeric(14, 6), nullable=True)
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_timestamp"), "audit_logs", ["timestamp"])
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_timestamp"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_column("recommendations", "realized_savings")
    op.drop_column("recommendations", "actual_cost_after")
    op.drop_column("recommendations", "verified_at")
    op.drop_column("recommendations", "implemented_at")
