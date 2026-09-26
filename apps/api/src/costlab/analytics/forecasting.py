"""Cost forecasting (Phase 7, CLAUDE.md §27).

Start simple, stay honest (§4, §27):
- two methods: a 14-day moving average and an OLS linear trend;
- the published `expected` blends both 50/50 — the moving average damps the
  linear extrapolation, the trend keeps it from being flat when the data is
  clearly rising;
- bounds come from the linear-fit residual standard deviation (an ~80%
  interval, ±1.28 sigma), never presented as a guarantee;
- the evaluation series is data-anchored (calendar-continuous; a missing day
  is a zero-cost day) and never uses the wall clock;
- a zero baseline is handled without division by zero and yields zero
  expected cost with LOW confidence;
- with fewer than 14 days of data the forecast reports `sufficient_data:
  false` instead of inventing numbers.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.analytics.cost import _money, get_bounds
from costlab.analytics.observability import forecast_runs_total
from costlab.db.models import CostRecord
from costlab.schemas.cost import CostFilters

MA_WINDOW_DAYS = 14
MIN_HISTORY_DAYS = 14
TREND_FIT_DAYS = 60  # OLS fit window (capped at available history)
Z_80 = 1.2816  # one-sided 80% normal quantile for the interval


@dataclass(frozen=True)
class ForecastPoint:
    date: date
    moving_average: float
    linear_trend: float
    expected: float
    lower_bound: float
    upper_bound: float


def _daily_series(session: Session, filters: CostFilters) -> list[tuple[date, float]]:
    """Calendar-continuous daily net-cost series (missing days filled with 0)."""
    bounds = get_bounds(session)
    if bounds is None:
        return []
    stmt = select(CostRecord.usage_date, func.sum(CostRecord.net_cost)).group_by(
        CostRecord.usage_date
    )
    if filters.start_date:
        stmt = stmt.where(CostRecord.usage_date >= filters.start_date)
    if filters.end_date:
        stmt = stmt.where(CostRecord.usage_date <= filters.end_date)
    if filters.project_id:
        stmt = stmt.where(CostRecord.project_id == filters.project_id)
    if filters.service:
        stmt = stmt.where(CostRecord.service_id == filters.service)
    if filters.environment:
        stmt = stmt.where(CostRecord.environment == filters.environment)
    if filters.region:
        stmt = stmt.where(CostRecord.region == filters.region)
    if filters.resource_id:
        stmt = stmt.where(CostRecord.resource_id == filters.resource_id)
    by_day = {day: _money(total) for day, total in session.execute(stmt).all()}
    series: list[tuple[date, float]] = []
    current = bounds.min_date
    while current <= bounds.max_date:
        series.append((current, by_day.get(current, 0.0)))
        current += timedelta(days=1)
    return series


def _linear_fit(values: list[float]) -> tuple[float, float, float, float]:
    """OLS fit over index-space. Returns (slope, intercept, sigma, r_squared)."""
    x = list(range(len(values)))
    fit = statistics.linear_regression(x, values)
    predicted = [fit.intercept + fit.slope * xi for xi in x]
    residuals = [y - p for y, p in zip(values, predicted, strict=False)]
    sigma = statistics.stdev(residuals) if len(residuals) > 2 else 0.0
    mean_y = sum(values) / len(values)
    ss_tot = sum((y - mean_y) ** 2 for y in values) or 1e-12
    ss_res = sum(r**2 for r in residuals)
    return fit.slope, fit.intercept, sigma, 1 - ss_res / ss_tot


def _confidence(n_history: int, sigma: float, mean_daily: float) -> str:
    if mean_daily <= 0:
        return "LOW"  # zero baseline — nothing meaningful to be confident about
    relative_sigma = sigma / mean_daily
    if n_history >= 45 and relative_sigma <= 0.35:
        return "HIGH"
    if n_history >= 21 and relative_sigma <= 0.6:
        return "MEDIUM"
    return "LOW"


def _trend_direction(slope: float, mean_daily: float) -> str:
    threshold = 0.005 * mean_daily if mean_daily > 0 else 0.0
    if slope > threshold:
        return "increasing"
    if slope < -threshold:
        return "decreasing"
    return "stable"


def build_forecast(
    session: Session, filters: CostFilters, horizon_days: int = 30
) -> dict[str, Any]:
    forecast_runs_total.labels(result="success").inc()
    series = _daily_series(session, filters)
    n = len(series)
    if n < MIN_HISTORY_DAYS:
        forecast_runs_total.labels(result="insufficient_data").inc()
        return {
            "sufficient_data": False,
            "message": (
                f"Insufficient data: forecasting needs at least {MIN_HISTORY_DAYS} days of "
                f"history, found {n}."
            ),
            "history_days": n,
            "horizon_days": horizon_days,
            "confidence": None,
            "forecast": [],
            "totals": None,
        }

    values = [value for _, value in series]
    last_day = series[-1][0]
    mean_daily = sum(values) / n

    # Method 1: moving average — the recent daily level, held flat.
    ma = sum(values[-MA_WINDOW_DAYS:]) / MA_WINDOW_DAYS
    # Method 2: OLS linear trend over the fit window.
    fit_values = values[-TREND_FIT_DAYS:]
    slope, intercept, sigma, r_squared = _linear_fit(fit_values)

    points: list[ForecastPoint] = []
    for offset in range(1, horizon_days + 1):
        day = last_day + timedelta(days=offset)
        linear_value = max(0.0, intercept + slope * (len(fit_values) - 1 + offset))
        expected = 0.5 * ma + 0.5 * linear_value
        half_width = Z_80 * sigma
        points.append(
            ForecastPoint(
                date=day,
                moving_average=round(ma, 4),
                linear_trend=round(linear_value, 4),
                expected=round(expected, 4),
                lower_bound=round(max(0.0, expected - half_width), 4),
                upper_bound=round(expected + half_width, 4),
            )
        )

    return {
        "sufficient_data": True,
        "message": None,
        "history_days": n,
        "history": {
            "start": series[0][0].isoformat(),
            "end": last_day.isoformat(),
            "daily_average": round(mean_daily, 4),
        },
        "horizon_days": horizon_days,
        "methods": {
            "moving_average": {
                "window_days": MA_WINDOW_DAYS,
                "level": round(ma, 4),
            },
            "linear_trend": {
                "fit_days": len(fit_values),
                "slope_per_day": round(slope, 6),
                "r_squared": round(r_squared, 3),
            },
        },
        "trend": _trend_direction(slope, mean_daily),
        # ~80% interval from the linear-fit residuals; costs cannot be negative,
        # so the lower bound is floored at zero.
        "interval": "80% (±1.28 residual sigma)",
        "confidence": _confidence(n, sigma, mean_daily),
        "forecast": [
            {
                "date": point.date.isoformat(),
                "moving_average": point.moving_average,
                "linear_trend": point.linear_trend,
                "expected": point.expected,
                "lower_bound": point.lower_bound,
                "upper_bound": point.upper_bound,
            }
            for point in points
        ],
        "totals": {
            "expected_30d": round(sum(point.expected for point in points), 2),
            "lower_bound_30d": round(sum(point.lower_bound for point in points), 2),
            "upper_bound_30d": round(sum(point.upper_bound for point in points), 2),
        },
    }
