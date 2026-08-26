"""Unit tests for cost analytics service."""

from datetime import date

import pytest

from app.services.cost_service import CostService
from app.services.mock_data import generate_cost_records, PROJECTS, SERVICES, RESOURCES


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
