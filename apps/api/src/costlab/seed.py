"""Seed the demo dataset into PostgreSQL (mock provider only).

Usage (from the repository root or apps/api):
    python -m costlab.seed           # seed only when the database is empty
    python -m costlab.seed --force   # replace existing demo fact rows

Safety: refuses to run when DEMO_MODE is false, and never touches a database
that already contains cost rows unless --force is given.
"""

from __future__ import annotations

import argparse
import logging
import sys
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.config import get_settings
from costlab.db.models import Budget
from costlab.db.session import SessionLocal
from costlab.governance import ensure_default_policies
from costlab.ingestion.loader import cost_record_count, ingest_snapshot
from costlab.logging_config import setup_logging
from costlab.providers import build_providers
from costlab.recommendations.engine import run_engine

logger = logging.getLogger("costlab.seed")


def _ensure_demo_budget(session: Session) -> None:
    """Seed one demo budget ($50/month, 70/90 thresholds) when none exists."""
    existing = session.execute(select(func.count()).select_from(Budget)).scalar_one()
    if existing:
        return
    session.add(
        Budget(
            id=uuid4().hex,
            name="Lab monthly budget",
            scope_type="all",
            scope_value=None,
            period="monthly",
            limit_amount=50,
            warning_threshold=70,
            critical_threshold=90,
        )
    )
    session.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the Cloud Cost Lab demo dataset.")
    parser.add_argument(
        "--force", action="store_true", help="Replace existing cost/usage rows (demo data only)."
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    setup_logging(settings.log_level)

    if not settings.demo_mode:
        logger.error(
            "Refusing to seed: DEMO_MODE is false. Demo seeding is only allowed in demo mode."
        )
        return 1

    providers = build_providers(settings)
    snapshot = providers.billing.load_snapshot()
    usage_records = providers.usage.load_usage()

    with SessionLocal() as session:
        existing = cost_record_count(session)
        if existing > 0 and not args.force:
            # Fact rows are already present, but definitions/config are still
            # ensured (idempotent) so upgrades fill in new Phase 6 rows.
            ensure_default_policies(session)
            _ensure_demo_budget(session)
            session.commit()
            logger.info(
                "database already contains demo data; ensured policies/budget "
                "(use --force to replace facts)",
                extra={"details": {"existing_cost_records": existing}},
            )
            return 0
        result = ingest_snapshot(session, snapshot, usage_records, replace_facts=existing > 0)
        session.commit()
        # Recommendation mode only: writes recommendation rows to THIS database,
        # never touches cloud infrastructure (CLAUDE.md §38).
        run_engine(session)
        ensure_default_policies(session)
        _ensure_demo_budget(session)
        session.commit()

    logger.info(
        "demo data seeded",
        extra={
            "details": {
                "source": result.source,
                "services": result.services,
                "projects": result.projects,
                "resources": result.resources,
                "cost_records": result.cost_records,
                "usage_records": result.usage_records,
            }
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
