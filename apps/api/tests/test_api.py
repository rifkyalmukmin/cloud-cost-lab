"""API integration tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoints:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["demo_mode"] is True

    def test_ready(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["data_loaded"] is True


class TestCostAPI:
    def test_cost_summary(self, client):
        response = client.get("/api/cost")
        assert response.status_code == 200
        data = response.json()
        assert "current_month_cost" in data
        assert "previous_month_cost" in data
        assert "mom_change_percent" in data
        assert data["currency"] == "USD"

    def test_cost_summary_with_date(self, client):
        response = client.get("/api/cost?reference_date=2026-08-20")
        assert response.status_code == 200
        data = response.json()
        assert data["current_month_cost"] > 0

    def test_cost_trend(self, client):
        response = client.get("/api/cost/trend")
        assert response.status_code == 200
        data = response.json()
        assert "daily_costs" in data
        assert len(data["daily_costs"]) == 30
        assert data["total_cost"] > 0

    def test_cost_trend_custom_range(self, client):
        response = client.get("/api/cost/trend?start_date=2026-08-01&end_date=2026-08-10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["daily_costs"]) == 10

    def test_cost_by_service(self, client):
        response = client.get("/api/cost/by-service")
        assert response.status_code == 200
        data = response.json()
        assert "breakdown" in data
        assert len(data["breakdown"]) > 0
        services = {b["value"] for b in data["breakdown"]}
        assert "Compute Engine" in services

    def test_cost_by_project(self, client):
        response = client.get("/api/cost/by-project")
        assert response.status_code == 200
        data = response.json()
        assert "breakdown" in data
        assert len(data["breakdown"]) == 3

    def test_cost_by_environment(self, client):
        response = client.get("/api/cost/by-environment")
        assert response.status_code == 200
        data = response.json()
        assert "breakdown" in data
        envs = {b["value"] for b in data["breakdown"]}
        assert "production" in envs
        assert "development" in envs

    def test_invalid_date_format(self, client):
        response = client.get("/api/cost/trend?start_date=invalid")
        assert response.status_code == 422
