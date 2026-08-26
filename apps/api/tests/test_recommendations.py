"""Tests for recommendation engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.recommendations.rules import (
    IdleComputeRule,
    OversizedComputeRule,
    UnusedDiskRule,
    StorageRetentionRule,
    CostAnomalyRule,
)
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return RecommendationService()


class TestIdleComputeRule:
    def test_idle_compute_cpu_0(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "development", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 0.0}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "HIGH"

    def test_idle_compute_cpu_2(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 2.0}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "MEDIUM"

    def test_idle_compute_cpu_4_9(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "development", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 4.9}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "MEDIUM"

    def test_not_idle_cpu_5(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "development", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 5.0}
        assert rule.evaluate(resource, metrics) is False

    def test_not_idle_cpu_10(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "development", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 10.0}
        assert rule.evaluate(resource, metrics) is False

    def test_idle_compute_null_cpu(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "development", "monthly_cost": 50.0}
        metrics = {"cpu_avg": None}
        assert rule.evaluate(resource, metrics) is False

    def test_idle_compute_not_compute_service(self):
        rule = IdleComputeRule()
        resource = {"service": "Cloud Storage", "environment": "production", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 1.0}
        assert rule.evaluate(resource, metrics) is False

    def test_idle_compute_production_risk_medium(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 2.0}
        assert rule.calculate_risk(resource, metrics) == "MEDIUM"

    def test_idle_compute_dev_risk_low(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "development", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 2.0}
        assert rule.calculate_risk(resource, metrics) == "LOW"

    def test_idle_compute_saving_90_percent(self):
        rule = IdleComputeRule()
        resource = {"service": "Compute Engine", "environment": "development", "monthly_cost": 50.0}
        metrics = {"cpu_avg": 2.0}
        saving = rule.calculate_saving(resource, metrics)
        assert saving == 45.0


class TestOversizedComputeRule:
    def test_oversized_cpu_5_mem_10(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 5.0, "memory_avg": 10.0}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "HIGH"

    def test_oversized_cpu_15_mem_30(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 15.0, "memory_avg": 30.0}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "MEDIUM"

    def test_oversized_cpu_19_mem_39(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 19.0, "memory_avg": 39.0}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "MEDIUM"

    def test_not_oversized_cpu_20(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 20.0, "memory_avg": 30.0}
        assert rule.evaluate(resource, metrics) is False

    def test_not_oversized_mem_40(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 15.0, "memory_avg": 40.0}
        assert rule.evaluate(resource, metrics) is False

    def test_oversized_null_cpu(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": None, "memory_avg": 20.0}
        assert rule.evaluate(resource, metrics) is False

    def test_oversized_null_memory(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 15.0, "memory_avg": None}
        assert rule.evaluate(resource, metrics) is False

    def test_oversized_risk_low_cpu_under_10(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 8.0, "memory_avg": 20.0}
        assert rule.calculate_risk(resource, metrics) == "LOW"

    def test_oversized_risk_medium_cpu_15(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 15.0, "memory_avg": 20.0}
        assert rule.calculate_risk(resource, metrics) == "MEDIUM"

    def test_oversized_saving_40_percent(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 15.0, "memory_avg": 25.0}
        saving = rule.calculate_saving(resource, metrics)
        assert saving == 40.0

    def test_oversized_effort_medium(self):
        rule = OversizedComputeRule()
        resource = {"service": "Compute Engine", "environment": "production", "monthly_cost": 100.0}
        metrics = {"cpu_avg": 15.0, "memory_avg": 25.0}
        assert rule.effort(resource, metrics) == "MEDIUM"


class TestUnusedDiskRule:
    def test_unused_disk_unattached(self):
        rule = UnusedDiskRule()
        resource = {"service": "Compute Engine", "status": "unattached", "monthly_cost": 10.0}
        metrics = {}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "HIGH"
        assert rule.calculate_risk(resource, metrics) == "LOW"
        saving = rule.calculate_saving(resource, metrics)
        assert saving == 10.0

    def test_unused_disk_low_util(self):
        rule = UnusedDiskRule()
        resource = {"service": "Compute Engine", "status": "active", "monthly_cost": 10.0}
        metrics = {"disk_avg": 5.0}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "MEDIUM"

    def test_not_unused_disk_util_10(self):
        rule = UnusedDiskRule()
        resource = {"service": "Compute Engine", "status": "active", "monthly_cost": 10.0}
        metrics = {"disk_avg": 10.0}
        assert rule.evaluate(resource, metrics) is False

    def test_unused_disk_null_util(self):
        rule = UnusedDiskRule()
        resource = {"service": "Compute Engine", "status": "active", "monthly_cost": 10.0}
        metrics = {"disk_avg": None}
        assert rule.evaluate(resource, metrics) is False


class TestStorageRetentionRule:
    def test_storage_retention_applies(self):
        rule = StorageRetentionRule()
        resource = {"service": "Cloud Storage", "monthly_cost": 5.0}
        metrics = {}
        assert rule.evaluate(resource, metrics) is True
        assert rule.calculate_risk(resource, metrics) == "LOW"
        assert rule.confidence(resource, metrics) == "MEDIUM"

    def test_storage_retention_artifact_registry(self):
        rule = StorageRetentionRule()
        resource = {"service": "Artifact Registry", "monthly_cost": 5.0}
        metrics = {}
        assert rule.evaluate(resource, metrics) is True

    def test_storage_retention_not_storage(self):
        rule = StorageRetentionRule()
        resource = {"service": "Compute Engine", "monthly_cost": 50.0}
        metrics = {}
        assert rule.evaluate(resource, metrics) is False

    def test_storage_retention_cost_too_low(self):
        rule = StorageRetentionRule()
        resource = {"service": "Cloud Storage", "monthly_cost": 0.5}
        metrics = {}
        assert rule.evaluate(resource, metrics) is False

    def test_storage_retention_saving(self):
        rule = StorageRetentionRule()
        resource = {"service": "Cloud Storage", "monthly_cost": 10.0}
        metrics = {}
        saving = rule.calculate_saving(resource, metrics)
        assert saving == 3.0


class TestCostAnomalyRule:
    def test_cost_anomaly_detected(self):
        rule = CostAnomalyRule()
        resource = {"service": "Compute Engine", "monthly_cost": 150.0}
        metrics = {"cost_change_pct": 60.0}
        assert rule.evaluate(resource, metrics) is True
        assert rule.confidence(resource, metrics) == "HIGH"

    def test_cost_anomaly_not_detected(self):
        rule = CostAnomalyRule()
        resource = {"service": "Compute Engine", "monthly_cost": 100.0}
        metrics = {"cost_change_pct": 20.0}
        assert rule.evaluate(resource, metrics) is False

    def test_cost_anomaly_saving_zero(self):
        rule = CostAnomalyRule()
        resource = {"service": "Compute Engine", "monthly_cost": 150.0}
        metrics = {"cost_change_pct": 60.0}
        saving = rule.calculate_saving(resource, metrics)
        assert saving == 0.0


class TestRecommendationService:
    def test_generate_recommendations(self, service):
        recommendations = service.generate_recommendations()
        assert len(recommendations) > 0

    def test_recommendations_have_required_fields(self, service):
        recommendations = service.generate_recommendations()
        for rec in recommendations:
            assert "id" in rec
            assert "title" in rec
            assert "resource_id" in rec
            assert "problem" in rec
            assert "evidence" in rec
            assert "recommendation" in rec
            assert "current_cost" in rec
            assert "potential_cost" in rec
            assert "potential_savings" in rec
            assert "savings_percentage" in rec
            assert "risk" in rec
            assert "confidence" in rec
            assert "effort" in rec
            assert "priority" in rec
            assert "status" in rec
            assert "approval_required" in rec

    def test_recommendations_sorted_by_priority(self, service):
        recommendations = service.generate_recommendations()
        priorities = [r["priority"] for r in recommendations]
        assert priorities == sorted(priorities, reverse=True)

    def test_all_recommendations_require_approval(self, service):
        recommendations = service.generate_recommendations()
        for rec in recommendations:
            assert rec["approval_required"] is True

    def test_all_recommendations_open_status(self, service):
        recommendations = service.generate_recommendations()
        for rec in recommendations:
            assert rec["status"] == "OPEN"

    def test_get_recommendation_by_id(self, service):
        recommendations = service.generate_recommendations()
        if recommendations:
            rec_id = recommendations[0]["id"]
            rec = service.get_recommendation(rec_id)
            assert rec is not None
            assert rec["id"] == rec_id

    def test_get_recommendation_not_found(self, service):
        rec = service.get_recommendation("nonexistent-id")
        assert rec is None


class TestRecommendationAPI:
    def test_list_recommendations(self, client):
        response = client.get("/api/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "total" in data

    def test_get_recommendation_detail(self, client):
        list_response = client.get("/api/recommendations")
        recommendations = list_response.json()["recommendations"]
        if recommendations:
            rec_id = recommendations[0]["id"]
            response = client.get(f"/api/recommendations/{rec_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == rec_id

    def test_get_recommendation_not_found(self, client):
        response = client.get("/api/recommendations/nonexistent")
        assert response.status_code == 404
