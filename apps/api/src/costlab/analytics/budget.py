"""Budget analytics (Phase 6, CLAUDE.md §15).

Rules carried over from earlier phases:
- the evaluation month is the latest month IN THE DATA, never the wall clock;
- spend is the NET cost (after credits) — what is actually paid;
- the projected month-end is a linear run-rate and is always labelled an
  estimate;
- status thresholds are evaluated with inclusive boundaries: exactly at the
  warning threshold is already WARNING, exactly at the critical threshold is
  CRITICAL, and exactly at 100% is EXCEEDED (§15: Exceeded: 100%).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.analytics.cost import get_bounds
from costlab.db.models import Budget, CostRecord

BudgetScopeType = Literal["all", "project", "service", "environment"]
SCOPES = ("all", "project", "service", "environment")
BUDGET_STATUSES = ("HEALTHY", "WARNING", "CRITICAL", "EXCEEDED")


@dataclass(frozen=True)
class SpendWindow:
    """Month-to-date window of the latest month in the data."""

    month_start: date
    data_end: date
    days_elapsed: int
    days_in_month: int


@dataclass(frozen=True)
class Spend:
    amount: float
    gross_amount: float
    window: SpendWindow
    daily_average: float
    projected_month_end: float
    projected_remaining_days_basis: int


def budget_status(spend: float, limit: float, warning_pct: float, critical_pct: float) -> str:
    """HEALTHY / WARNING / CRITICAL / EXCEEDED — inclusive threshold boundaries.

    With the default warning=70 / critical=90:
      69% -> HEALTHY, 70% -> WARNING, 89% -> WARNING, 90% -> CRITICAL,
      99% -> CRITICAL, 100% -> EXCEEDED, 101% -> EXCEEDED.
    """
    if limit <= 0:
        return "EXCEEDED"  # a zero/negative limit cannot be satisfied
    pct = spend / limit * 100
    if pct >= 100:
        return "EXCEEDED"
    if pct >= critical_pct:
        return "CRITICAL"
    if pct >= warning_pct:
        return "WARNING"
    return "HEALTHY"


def budget_window(session: Session) -> SpendWindow | None:
    """Latest month in the data, anchored to the data (not the wall clock)."""
    bounds = get_bounds(session)
    if bounds is None:
        return None
    month_start = bounds.max_date.replace(day=1)
    days_in_month = calendar.monthrange(bounds.max_date.year, bounds.max_date.month)[1]
    days_elapsed = (bounds.max_date - month_start).days + 1
    return SpendWindow(
        month_start=month_start,
        data_end=bounds.max_date,
        days_elapsed=days_elapsed,
        days_in_month=days_in_month,
    )


def _scope_filters(budget: Budget) -> list[Any]:
    """Cost-record filters implementing the budget scope."""
    conditions = []
    if budget.scope_type == "project":
        conditions.append(CostRecord.project_id == budget.scope_value)
    elif budget.scope_type == "service":
        conditions.append(CostRecord.service_id == budget.scope_value)
    elif budget.scope_type == "environment":
        conditions.append(CostRecord.environment == budget.scope_value)
    return conditions


def budget_spend(session: Session, budget: Budget, window: SpendWindow) -> Spend:
    """Net + gross spend inside the budget scope for the evaluation month."""
    stmt = select(
        func.coalesce(func.sum(CostRecord.net_cost), 0),
        func.coalesce(func.sum(CostRecord.cost), 0),
    ).where(CostRecord.usage_date >= window.month_start, CostRecord.usage_date <= window.data_end)
    for condition in _scope_filters(budget):
        stmt = stmt.where(condition)
    net, gross = session.execute(stmt).one()

    net_amount = float(net)
    # Linear run-rate projection (estimate): daily average over the elapsed
    # days times the full length of the month.
    projected = net_amount / window.days_elapsed * window.days_in_month
    return Spend(
        amount=round(net_amount, 4),
        gross_amount=round(float(gross), 4),
        window=window,
        daily_average=round(net_amount / window.days_elapsed, 4),
        projected_month_end=round(projected, 2),
        projected_remaining_days_basis=window.days_in_month - window.days_elapsed,
    )


def evaluate_budget(session: Session, budget: Budget) -> dict[str, Any]:
    """Full read-time evaluation for one budget."""
    window = budget_window(session)
    if window is None:
        return {
            "id": budget.id,
            "name": budget.name,
            "scope_type": budget.scope_type,
            "scope_value": budget.scope_value,
            "period": budget.period,
            "limit": float(budget.limit_amount),
            "warning_threshold": float(budget.warning_threshold),
            "critical_threshold": float(budget.critical_threshold),
            "status": None,
            "spend": None,
            "remaining": None,
            "spend_percentage": None,
            "projected_month_end": None,
            "forecast_over_budget": None,
        }
    spend = budget_spend(session, budget, window)
    limit = float(budget.limit_amount)
    warning = float(budget.warning_threshold)
    critical = float(budget.critical_threshold)
    status = budget_status(spend.amount, limit, warning, critical)
    return {
        "id": budget.id,
        "name": budget.name,
        "scope_type": budget.scope_type,
        "scope_value": budget.scope_value,
        "period": budget.period,
        "limit": limit,
        "warning_threshold": warning,
        "critical_threshold": critical,
        "status": status,
        "spend": {
            "amount": spend.amount,
            "gross_amount": spend.gross_amount,
            "daily_average": spend.daily_average,
            "period": {
                "start": window.month_start.isoformat(),
                "end": window.data_end.isoformat(),
                "days_elapsed": window.days_elapsed,
                "days_in_month": window.days_in_month,
            },
        },
        "remaining": round(limit - spend.amount, 4),
        "spend_percentage": round(spend.amount / limit * 100, 1) if limit > 0 else None,
        # Linear run-rate estimate — labelled as such in the UI/docs (§15).
        "projected_month_end": spend.projected_month_end,
        "forecast_over_budget": spend.projected_month_end > limit,
    }


def list_budgets(session: Session) -> list[dict[str, Any]]:
    return [
        evaluate_budget(session, budget)
        for budget in session.execute(select(Budget).order_by(Budget.created_at)).scalars()
    ]
