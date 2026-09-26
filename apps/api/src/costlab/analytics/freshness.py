"""Data freshness (Phase 8, CLAUDE.md §41).

Billing data always lags reality. `last_updated` is the newest day in the
data (treated as complete at the END of that UTC day); `data_age_hours` is
measured against the wall clock; the status is:

- FRESH   — age <= max_age_hours
- STALE   — age >  max_age_hours
- UNKNOWN — there is no data at all

Stale data is never presented as current: the dashboard surfaces the status
and age next to every fresh-looking number via `GET /api/freshness`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class Freshness:
    status: str  # FRESH | STALE | UNKNOWN
    last_updated: str | None  # ISO date the data is complete through
    data_age_hours: float | None
    max_age_hours: float = 48.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "last_updated": self.last_updated,
            "data_age_hours": round(self.data_age_hours, 1)
            if self.data_age_hours is not None
            else None,
            "max_age_hours": self.max_age_hours,
        }


def compute_freshness(
    newest_data_date: date | None,
    now: datetime,
    max_age_hours: float = 48.0,
) -> Freshness:
    """Pure freshness computation (unit-testable without a database)."""
    if newest_data_date is None:
        return Freshness(
            status="UNKNOWN", last_updated=None, data_age_hours=None, max_age_hours=max_age_hours
        )
    # The newest day counts as complete at the END of that UTC day.
    data_complete_at = datetime.combine(
        newest_data_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC
    )
    now_utc = now if now.tzinfo else now.replace(tzinfo=UTC)
    age_hours = max(0.0, (now_utc - data_complete_at).total_seconds() / 3600)
    status = "FRESH" if age_hours <= max_age_hours else "STALE"
    return Freshness(
        status=status,
        last_updated=newest_data_date.isoformat(),
        data_age_hours=age_hours,
        max_age_hours=max_age_hours,
    )
