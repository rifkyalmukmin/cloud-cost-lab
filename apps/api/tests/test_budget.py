"""Tests for budget monitoring system."""

import pytest
from app.main import app
from app.services.budget_service import BudgetService
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return BudgetService()


class TestBudgetService:
    def test_status_healthy_below_warning(self, service):
        status = service._calculate_status(69.0)
        assert status == "HEALTHY"

    def test_status_warning_at_70(self, service):
        status = service._calculate_status(70.0)
        assert status == "WARNING"

    def test_status_warning_at_89(self, service):
        status = service._calculate_status(89.0)
        assert status == "WARNING"

    def test_status_critical_at_90(self, service):
        status = service._calculate_status(90.0)
        assert status == "CRITICAL"

    def test_status_critical_at_99(self, service):
        status = service._calculate_status(99.0)
        assert status == "CRITICAL"

    def test_status_exceeded_at_100(self, service):
        status = service._calculate_status(100.0)
        assert status == "EXCEEDED"

    def test_status_exceeded_at_101(self, service):
        status = service._calculate_status(101.0)
        assert status == "EXCEEDED"

    def test_budget_status_structure(self, service):
        result = service.get_budget_status()
        assert "budget" in result
        assert "current" in result
        assert "projected" in result
        assert "alerts" in result

    def test_budget_has_required_fields(self, service):
        result = service.get_budget_status()
        budget = result["budget"]
        assert "id" in budget
        assert "name" in budget
        assert "scope" in budget
        assert "period" in budget
        assert "limit" in budget
        assert "warning_threshold" in budget
        assert "critical_threshold" in budget

    def test_current_spend_has_fields(self, service):
        result = service.get_budget_status()
        current = result["current"]
        assert "spend" in current
        assert "utilization_pct" in current
        assert "remaining" in current
        assert "status" in current

    def test_projected_spend_has_fields(self, service):
        result = service.get_budget_status()
        projected = result["projected"]
        assert "spend" in projected
        assert "utilization_pct" in projected
        assert "status" in projected

    def test_alerts_is_list(self, service):
        result = service.get_budget_status()
        assert isinstance(result["alerts"], list)

    def test_alert_has_severity(self, service):
        result = service.get_budget_status()
        for alert in result["alerts"]:
            assert "severity" in alert
            assert "message" in alert
            assert "recommendation" in alert


class TestBudgetAPI:
    def test_get_budget_status(self, client):
        response = client.get("/api/budget")
        assert response.status_code == 200
        data = response.json()
        assert "budget" in data
        assert "current" in data
        assert "projected" in data

    def test_budget_with_date(self, client):
        response = client.get("/api/budget?reference_date=2026-08-20")
        assert response.status_code == 200
