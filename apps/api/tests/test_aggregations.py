"""Cost aggregation unit tests (CLAUDE.md §54: business logic must be tested).

Expected values are recomputed in plain Python from data/mock/cost.json, so the
SQL aggregations are validated against an independent second implementation of
the same math.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from costlab.analytics import cost as analytics
from costlab.schemas.cost import CostFilters

MOCK_DIR = Path(__file__).resolve().parents[3] / "data" / "mock"
TOLERANCE = 1e-6


@pytest.fixture(scope="module")
def expected() -> dict:
    """Independent aggregation of the committed mock dataset."""
    rows = json.loads((MOCK_DIR / "cost.json").read_text(encoding="utf-8"))
    by_month: dict[str, Decimal] = defaultdict(Decimal)
    by_service: dict[str, Decimal] = defaultdict(Decimal)
    by_project: dict[str, Decimal] = defaultdict(Decimal)
    by_environment: dict[str, Decimal] = defaultdict(Decimal)
    total = Decimal("0")
    credits_total = Decimal("0")
    for row in rows:
        cost = Decimal(str(row["cost"]))
        by_month[row["usage_date"][:7]] += cost
        by_service[row["service_id"]] += cost
        by_project[row["project_id"]] += cost
        by_environment[row["environment"]] += cost
        total += cost
        credits_total += Decimal(str(row["credits"]))
    return {
        "rows": len(rows),
        "by_month": {k: round(float(v), 4) for k, v in by_month.items()},
        "by_service": {k: round(float(v), 4) for k, v in by_service.items()},
        "by_project": {k: round(float(v), 4) for k, v in by_project.items()},
        "by_environment": {k: round(float(v), 4) for k, v in by_environment.items()},
        "total": round(float(total), 4),
        "credits": round(float(credits_total), 4),
        "net": round(float(total - credits_total), 4),
        "months": sorted(by_month),
    }


def test_monthly_cost_matches_source(db_session, expected) -> None:
    points = analytics.cost_trend(db_session, CostFilters(), "month")
    assert {p.period.strftime("%Y-%m"): p.cost for p in points} == pytest.approx(
        expected["by_month"], abs=TOLERANCE
    )


def test_monthly_costs_rise_over_time(db_session) -> None:
    """The dataset tells a rising-cost story (mock scenario requirement)."""
    points = analytics.cost_trend(db_session, CostFilters(), "month")
    full_months = [p.cost for p in points if p.period.month in (6, 7, 8)]
    assert full_months == sorted(full_months), f"monthly cost must rise: {full_months}"


def test_daily_trend_sums_to_total(db_session, expected) -> None:
    points = analytics.cost_trend(db_session, CostFilters(), "day")
    assert len(points) == 97  # 2026-06-01 .. 2026-09-05
    assert sum(p.cost for p in points) == pytest.approx(expected["total"], abs=0.01)


def test_weekly_trend_sums_to_total(db_session, expected) -> None:
    points = analytics.cost_trend(db_session, CostFilters(), "week")
    assert len(points) == 14
    # weeks are Monday-start buckets
    assert all(p.period.weekday() == 0 for p in points)
    assert sum(p.cost for p in points) == pytest.approx(expected["total"], abs=0.01)


def test_summary_cost_credits_net(db_session, expected) -> None:
    summary = analytics.cost_summary(db_session, CostFilters())
    assert summary.cost == pytest.approx(expected["total"], abs=TOLERANCE)
    assert summary.credits == pytest.approx(expected["credits"], abs=TOLERANCE)
    assert summary.net_cost == pytest.approx(expected["net"], abs=TOLERANCE)
    assert summary.net_cost == pytest.approx(summary.cost - summary.credits, abs=TOLERANCE)


def test_service_cost_matches_source(db_session, expected) -> None:
    rows = analytics.cost_by_service(db_session, CostFilters())
    assert {r.key: r.cost for r in rows} == pytest.approx(expected["by_service"], abs=TOLERANCE)
    # ordered by cost, descending
    costs = [r.cost for r in rows]
    assert costs == sorted(costs, reverse=True)


def test_project_cost_matches_source(db_session, expected) -> None:
    rows = analytics.cost_by_project(db_session, CostFilters())
    assert {r.key: r.cost for r in rows} == pytest.approx(expected["by_project"], abs=TOLERANCE)


def test_environment_cost_matches_source(db_session, expected) -> None:
    rows = analytics.cost_by_environment(db_session, CostFilters())
    assert {r.key: r.cost for r in rows} == pytest.approx(expected["by_environment"], abs=TOLERANCE)
    assert set(r.key for r in rows) == {"development", "staging", "production"}


def test_filters_narrow_totals(db_session, expected) -> None:
    summary = analytics.cost_summary(db_session, CostFilters(service="compute-engine"))
    assert summary.cost == pytest.approx(expected["by_service"]["compute-engine"], abs=TOLERANCE)

    summary = analytics.cost_summary(db_session, CostFilters(environment="production"))
    assert summary.cost == pytest.approx(expected["by_environment"]["production"], abs=TOLERANCE)

    summary = analytics.cost_summary(db_session, CostFilters(project_id="cc-lab-shop-prod"))
    assert summary.cost == pytest.approx(expected["by_project"]["cc-lab-shop-prod"], abs=TOLERANCE)


def test_combined_filters_intersect(db_session, expected) -> None:
    """Filters must combine with AND semantics."""
    rows = json.loads((MOCK_DIR / "cost.json").read_text(encoding="utf-8"))
    expected_total = round(
        float(
            sum(
                Decimal(str(r["cost"]))
                for r in rows
                if r["service_id"] == "cloud-sql" and r["environment"] == "staging"
            )
        ),
        4,
    )
    summary = analytics.cost_summary(
        db_session, CostFilters(service="cloud-sql", environment="staging")
    )
    assert summary.cost == pytest.approx(expected_total, abs=TOLERANCE)


def test_period_filter(db_session, expected) -> None:
    summary = analytics.cost_summary(
        db_session, CostFilters(start_date=date(2026, 8, 1), end_date=date(2026, 8, 31))
    )
    assert summary.cost == pytest.approx(expected["by_month"]["2026-08"], abs=TOLERANCE)


def test_list_cost_records_pagination(db_session, expected) -> None:
    rows, total = analytics.list_cost_records(db_session, CostFilters(), page=1, page_size=10)
    assert total == expected["rows"]
    assert len(rows) == 10
    # newest first
    dates = [r.usage_date for r in rows]
    assert dates == sorted(dates, reverse=True)
    # the last page holds the remaining rows; one past it is empty
    last_rows, _ = analytics.list_cost_records(db_session, CostFilters(), page=117, page_size=10)
    assert len(last_rows) == expected["rows"] - 1160
    beyond_rows, _ = analytics.list_cost_records(db_session, CostFilters(), page=118, page_size=10)
    assert beyond_rows == []


def test_unallocated_labels_flow_through(db_session) -> None:
    """The legacy sandbox resource carries no team/owner/application labels."""
    rows, _ = analytics.list_cost_records(
        db_session, CostFilters(project_id="cc-lab-legacy-sandbox"), 1, 5
    )
    assert rows
    assert all(r.labels.get("team") is None for r in rows)


def test_invalid_filter_range_rejected() -> None:
    with pytest.raises(ValueError, match="start_date"):
        CostFilters(start_date=date(2026, 8, 1), end_date=date(2026, 7, 1))
