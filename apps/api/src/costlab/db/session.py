"""Session management."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from costlab.db.engine import get_engine

SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
