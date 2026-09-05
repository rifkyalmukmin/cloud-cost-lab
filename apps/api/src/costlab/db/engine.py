"""SQLAlchemy engine factory."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from costlab.config import Settings, get_settings


@lru_cache
def get_engine(settings: Settings | None = None) -> Engine:
    """Create (once) the engine for the configured database.

    Connections are established lazily; a wrong URL only fails when the
    database is actually used, so `/health` works without PostgreSQL.
    """
    settings = settings or get_settings()
    return create_engine(
        settings.sync_database_url,
        pool_pre_ping=True,  # survive idle connection drops
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
        future=True,
    )
