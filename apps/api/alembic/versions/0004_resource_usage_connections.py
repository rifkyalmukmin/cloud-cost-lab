"""resource_usage.connections column (Phase 9 monitoring)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("resource_usage", sa.Column("connections", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("resource_usage", "connections")
