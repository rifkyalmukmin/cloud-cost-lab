"""Tests for cost forecasting."""

import pytest
from app.main import app
from app.services.forecast_service import ForecastService
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return ForecastService()


class TestForecastService:
    def test_forecast_has_required_fields(self, service):
        result = service.forecast_cost()
        assert "period_start" in result
        assert "period_end" in result
        assert "method" in result
        assert "daily_forecast" in result
        assert "monthly_summary" in result

    def test_daily_forecast_has_confidence_range(self, service):
        result = service.forecast_cost()
        for day in result["daily_forecast"]:
            assert "date" in day
            assert "expected" in day
            assert "lower_bound" in day
            assert "upper_bound" in day
            assert "confidence" in day

    def test_lower_bound_less_than_expected(self, service):
        result = service.forecast_cost()
        for day in result["daily_forecast"]:
            assert day["lower_bound"] <= day["expected"]

    def test_expected_less_than_upper_bound(self, service):
        result = service.forecast_cost()
        for day in result["daily_forecast"]:
            assert day["expected"] <= day["upper_bound"]

    def test_forecast_30_days(self, service):
        result = service.forecast_cost(days_ahead=30)
        assert len(result["daily_forecast"]) == 30

    def test_forecast_7_days(self, service):
        result = service.forecast_cost(days_ahead=7)
        assert len(result["daily_forecast"]) == 7

    def test_monthly_summary_has_range(self, service):
        result = service.forecast_cost()
        summary = result["monthly_summary"]
        assert "expected" in summary
        assert "lower_bound" in summary
        assert "upper_bound" in summary
        assert "range_description" in summary

    def test_monthly_summary_bounds(self, service):
        result = service.forecast_cost()
        summary = result["monthly_summary"]
        assert summary["lower_bound"] <= summary["expected"] <= summary["upper_bound"]


class TestForecastAPI:
    def test_get_forecast(self, client):
        response = client.get("/api/forecast")
        assert response.status_code == 200
        data = response.json()
        assert "daily_forecast" in data
        assert "monthly_summary" in data

    def test_forecast_with_days_ahead(self, client):
        response = client.get("/api/forecast?days_ahead=15")
        assert response.status_code == 200
        data = response.json()
        assert len(data["daily_forecast"]) == 15

    def test_forecast_with_date(self, client):
        response = client.get("/api/forecast?reference_date=2026-08-20")
        assert response.status_code == 200
        data = response.json()
        assert data["period_start"] == "2026-08-20"
