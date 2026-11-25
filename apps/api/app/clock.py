"""Dates the product treats as today.

Demo mode stays on the frozen billing snapshot of 26 August 2026.
Live mode uses the real calendar date.
"""

from datetime import date, datetime, timezone

from app.config import settings

DEMO_AS_OF = date(2026, 8, 26)
SNAPSHOT_LABEL = "data demo per 26 Agu 2026"


def reference_today() -> date:
    """Return the snapshot date in demo mode, otherwise today's date."""
    if settings.demo_mode:
        return DEMO_AS_OF
    return date.today()


def as_of_now() -> datetime:
    """Return noon on the snapshot date in demo mode, otherwise the current UTC time."""
    if settings.demo_mode:
        return datetime(2026, 8, 26, 12, 0, 0)
    return datetime.now(timezone.utc).replace(tzinfo=None)


def snapshot_label() -> str:
    """Label the frozen demo clock. Live mode has no snapshot label."""
    if settings.demo_mode:
        return SNAPSHOT_LABEL
    return ""
