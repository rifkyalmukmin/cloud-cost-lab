"""Savings verification (Phase 13, CLAUDE.md §23).

Distinguishes the two things FinOps must never confuse:

- **Potential savings** — a rule's estimate from pre-change evidence;
- **Realized savings** — an observed reduction measured AFTER the change was
  implemented. Only VERIFIED recommendations may carry it.

`compute_realized_savings` compares two equal-length windows of actual daily
net cost around the implementation date (30 days before vs up to 30 days
after, at least MIN_AFTER_DAYS required). It reports the monthly-equivalent
difference. A negative result (costs went up) is stored honestly — never
clamped to zero. When after-data does not exist yet, it returns None: there
is nothing realized to claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.analytics.cost import _money
from costlab.db.models import CostRecord
from costlab.db.models import Recommendation as RecommendationSum

BEFORE_WINDOW_DAYS = 30
AFTER_WINDOW_DAYS = 30
MIN_AFTER_DAYS = 7
DAYS_PER_MONTH = 30.0  # normalization constant for the monthly-equivalent rate


@dataclass(frozen=True)
class RealizedResult:
    realized_savings: float | None  # monthly-equivalent, may be negative
    before_daily_avg: float | None
    after_daily_avg: float | None
    before_days: int
    after_days: int
    source: str  # "data" | "reported"


def compute_realized_savings(
    session: Session,
    resource_id: str,
    implemented_on: date,
    reported_actual_cost_after: float | None = None,
) -> RealizedResult:
    """Before/after comparison from cost records when data exists.

    - before window: BEFORE_WINDOW_DAYS ending the day before implementation
    - after window: up to AFTER_WINDOW_DAYS starting on implementation day;
      needs at least MIN_AFTER_DAYS of data, otherwise returns realized=None
      (insufficient evidence — never invented).
    - if `reported_actual_cost_after` is supplied (an externally measured
      monthly cost), it is used directly and the source is "reported".
    """
    before_end = implemented_on - timedelta(days=1)
    before_start = before_end - timedelta(days=BEFORE_WINDOW_DAYS - 1)
    after_start = implemented_on
    after_end = after_start + timedelta(days=AFTER_WINDOW_DAYS - 1)

    def window_daily_avg(window_start: date, window_end: date) -> tuple[float | None, int]:
        row = session.execute(
            select(
                func.coalesce(func.sum(CostRecord.net_cost), 0),
                func.count(func.distinct(CostRecord.usage_date)),
            ).where(
                CostRecord.resource_id == resource_id,
                CostRecord.usage_date >= window_start,
                CostRecord.usage_date <= window_end,
            )
        ).one()
        days = int(row[1])
        if days == 0:
            return None, 0
        return _money(row[0]) / days, days

    before_daily, before_days = window_daily_avg(before_start, before_end)
    if before_daily is None:
        return RealizedResult(None, None, None, before_days, 0, "data")

    if reported_actual_cost_after is not None:
        reported_daily = reported_actual_cost_after / DAYS_PER_MONTH
        realized = (before_daily - reported_daily) * DAYS_PER_MONTH
        return RealizedResult(
            realized_savings=_money(realized),
            before_daily_avg=_money(before_daily),
            after_daily_avg=_money(reported_daily),
            before_days=before_days,
            after_days=0,
            source="reported",
        )

    after_daily: float | None
    after_days_int: int
    after_daily, after_days_int = window_daily_avg(after_start, after_end)
    after_days = after_days_int
    if after_daily is None or after_days < MIN_AFTER_DAYS:
        # Not enough post-change data: refuse to call anything realized.
        return RealizedResult(None, before_daily, None, before_days, after_days, "data")

    realized = (before_daily - after_daily) * DAYS_PER_MONTH
    return RealizedResult(
        realized_savings=_money(realized),
        before_daily_avg=_money(before_daily),
        after_daily_avg=_money(after_daily),
        before_days=before_days,
        after_days=after_days,
        source="data",
    )


def savings_summary(session: Session) -> dict[str, Any]:
    """Potential vs realized aggregates per lifecycle status."""

    def _sum_potential(statuses: list[str]) -> float:
        if not statuses:
            return 0.0
        value = session.execute(
            select(func.coalesce(func.sum(RecommendationSum.potential_savings), 0)).where(
                RecommendationSum.status.in_(statuses)
            )
        ).scalar_one()
        return _money(value)

    def _sum_realized() -> float:
        value = session.execute(
            select(func.coalesce(func.sum(RecommendationSum.realized_savings), 0)).where(
                RecommendationSum.status == "VERIFIED"
            )
        ).scalar_one()
        return _money(value)

    def _count(statuses: list[str]) -> int:
        return int(
            session.execute(
                select(func.count())
                .select_from(RecommendationSum)
                .where(RecommendationSum.status.in_(statuses))
            ).scalar_one()
        )

    potential_open = _sum_potential(["OPEN"])
    approved = _sum_potential(["APPROVED"])
    implemented = _sum_potential(["IMPLEMENTED"])
    verified = _sum_potential(["VERIFIED"])
    rejected = _sum_potential(["REJECTED"])
    realized = _sum_realized()

    return {
        "potential_savings": _money(potential_open + approved),
        "approved_savings": approved,
        "implemented": {
            "count": _count(["IMPLEMENTED"]),
            "potential_savings": implemented,
        },
        "verified": {
            "count": _count(["VERIFIED"]),
            "potential_savings": verified,
        },
        "realized_savings": realized,
        "rejected_savings_foregone": rejected,
        "by_status": {
            "OPEN": {"count": _count(["OPEN"]), "potential_savings": potential_open},
            "APPROVED": {"count": _count(["APPROVED"]), "potential_savings": approved},
            "IMPLEMENTED": {
                "count": _count(["IMPLEMENTED"]),
                "potential_savings": implemented,
            },
            "VERIFIED": {"count": _count(["VERIFIED"]), "potential_savings": verified},
            "REJECTED": {"count": _count(["REJECTED"]), "potential_savings": rejected},
        },
    }
