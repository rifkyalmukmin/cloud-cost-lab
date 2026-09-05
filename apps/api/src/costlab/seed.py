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

from costlab.config import get_settings
from costlab.db.session import SessionLocal
from costlab.ingestion.loader import cost_record_count, ingest_snapshot
from costlab.logging_config import setup_logging
from costlab.providers import build_providers

logger = logging.getLogger("costlab.seed")


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
            logger.info(
                "database already contains demo data; nothing to do (use --force to replace)",
                extra={"details": {"existing_cost_records": existing}},
            )
            return 0
        result = ingest_snapshot(session, snapshot, usage_records, replace_facts=existing > 0)
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
