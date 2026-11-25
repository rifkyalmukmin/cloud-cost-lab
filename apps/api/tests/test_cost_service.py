"""Unit tests for cost analytics service."""

import calendar
from datetime import date

import pytest
from app.clock import as_of_now, reference_today, snapshot_label
from app.config import settings
from app.providers.base import DataFreshness
from app.services.cost_service import CostService
from app.services.mock_data import PROJECTS, RESOURCES, SERVICES, generate_cost_records
from app.services.recommendation_service import recommendation_service


class TestMockData:
    def test_generates_records(self):
        records = generate_cost_records(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )
        assert len(records) > 0

    def test_deterministic(self):
        r1 = generate_cost_records(start_date=date(2026, 8, 1), end_date=date(2026, 8, 5))
        r2 = generate_cost_records(start_date=date(2026, 8, 1), end_date=date(2026, 8, 5))
        assert r1 == r2

    def test_records_per_day(self):
        records = generate_cost_records(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )
        assert len(records) == len(RESOURCES)

    def test_cost_positive(self):
        records = generate_cost_records(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )
        for r in records:
            assert r["cost"] > 0
            assert r["net_cost"] >= 0

    def test_all_services_present(self):
        records = generate_cost_records(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )
        services_found = {r["service_id"] for r in records}
        expected = {s["service_id"] for s in SERVICES}
        assert services_found == expected

    def test_all_projects_present(self):
        records = generate_cost_records(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )
        projects_found = {r["project_id"] for r in records}
        expected = {p["project_id"] for p in PROJECTS}
        assert projects_found == expected

    def test_environments_present(self):
        records = generate_cost_records(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )
        envs = {r["environment"] for r in records}
        assert "production" in envs
        assert "staging" in envs
        assert "development" in envs


class TestCostService:
    @pytest.fixture
    def service(self):
        return CostService()

    def test_summary_has_required_fields(self, service):
        summary = service.get_summary(reference_date=date(2026, 8, 26))
        assert "current_month_cost" in summary
        assert "previous_month_cost" in summary
        assert "mom_change_percent" in summary
        assert "average_daily_cost" in summary
        assert "projected_month_cost" in summary
        assert "potential_savings" in summary
        assert "currency" in summary
        assert "data_freshness" in summary
        assert "freshness_status" in summary
        assert summary["snapshot_label"] == "data demo per 26 Agu 2026"

    def test_potential_savings_uses_deduped_recommendations(self, service):
        summary = service.get_summary(reference_date=date(2026, 8, 26))
        expected = recommendation_service.total_potential_savings(date(2026, 8, 26))
        assert summary["potential_savings"] == expected
        assert summary["potential_savings"] != round(summary["current_month_cost"] * 0.18, 2)

    def test_summary_values_positive(self, service):
        summary = service.get_summary(reference_date=date(2026, 8, 26))
        assert summary["current_month_cost"] > 0
        assert summary["previous_month_cost"] > 0
        assert summary["average_daily_cost"] > 0
        assert summary["projected_month_cost"] > 0

    def test_mom_change_is_percentage(self, service):
        summary = service.get_summary(reference_date=date(2026, 8, 26))
        assert -100 <= summary["mom_change_percent"] <= 200

    def test_trend_has_daily_costs(self, service):
        trend = service.get_trend(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
        )
        assert "daily_costs" in trend
        assert len(trend["daily_costs"]) == 10
        assert "period_start" in trend
        assert "period_end" in trend
        assert "total_cost" in trend

    def test_trend_dates_ordered(self, service):
        trend = service.get_trend(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
        )
        dates = [d["date"] for d in trend["daily_costs"]]
        assert dates == sorted(dates)

    def test_by_service_breakdown(self, service):
        result = service.get_by_service(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 26),
        )
        assert "breakdown" in result
        assert len(result["breakdown"]) > 0
        total_pct = sum(b["percentage"] for b in result["breakdown"])
        assert 99.5 <= total_pct <= 100.5

    def test_by_project_breakdown(self, service):
        result = service.get_by_project(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 26),
        )
        assert "breakdown" in result
        assert len(result["breakdown"]) == len(PROJECTS)

    def test_by_environment_breakdown(self, service):
        result = service.get_by_environment(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 26),
        )
        assert "breakdown" in result
        envs = {b["value"] for b in result["breakdown"]}
        assert "production" in envs
        assert "staging" in envs
        assert "development" in envs

    def test_by_environment_percentages_sum_to_100(self, service):
        result = service.get_by_environment(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 26),
        )
        total_pct = sum(b["percentage"] for b in result["breakdown"])
        assert 99.5 <= total_pct <= 100.5

    def test_service_breakdown_sorted_by_cost(self, service):
        result = service.get_by_service(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 26),
        )
        costs = [b["total_cost"] for b in result["breakdown"]]
        assert costs == sorted(costs, reverse=True)


class _RowsProvider:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def get_cost_records(self, start_date=None, end_date=None):
        return self._rows

    def get_data_freshness(self):
        return DataFreshness(status="FRESH")

    def is_available(self):
        return True


def _cost_row(day: date, net_cost: float) -> dict:
    return {
        "usage_date": day,
        "net_cost": net_cost,
        "cost": net_cost,
        "service_name": "Compute Engine",
        "project_name": "Demo",
        "environment": "production",
    }


class TestMonthAlignment:
    def test_mom_ignores_days_after_the_same_day_number(self):
        rows = [
            _cost_row(date(2026, 7, 1), 10),
            _cost_row(date(2026, 7, 27), 50),
            _cost_row(date(2026, 7, 31), 80),
            _cost_row(date(2026, 8, 1), 12),
            _cost_row(date(2026, 8, 26), 8),
        ]
        summary = CostService(_RowsProvider(rows)).get_summary(reference_date=date(2026, 8, 26))
        assert summary["previous_month_cost"] == 10
        assert summary["current_month_cost"] == 20
        assert summary["month_length"] == 31
        assert summary["projected_month_cost"] == round((20 / 26) * 31, 2)

    def test_february_uses_the_calendar_length(self):
        summary = CostService(_RowsProvider([_cost_row(date(2026, 2, 1), 10)])).get_summary(
            reference_date=date(2026, 2, 1)
        )
        assert summary["month_length"] == 28
        assert summary["projected_month_cost"] == 280.0

    def test_live_mode_uses_today_without_a_snapshot_label(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_mode", False)
        assert reference_today() == date.today()
        assert as_of_now().date() == date.today()
        assert snapshot_label() == ""
        summary = CostService(_RowsProvider([])).get_summary()
        assert summary["snapshot_label"] == ""
        assert summary["month_length"] == calendar.monthrange(date.today().year, date.today().month)[1]
