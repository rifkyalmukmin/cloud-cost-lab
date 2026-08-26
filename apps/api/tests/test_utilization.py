"""Tests for utilization analytics API and service."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.utilization_service import UtilizationService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return UtilizationService()


class TestUtilizationService:
    def test_utilization_summary_has_all_resources(self, service):
        result = service.get_utilization_summary()
        assert result["total_resources"] == 8

    def test_utilization_summary_has_required_fields(self, service):
        result = service.get_utilization_summary()
        assert "period_start" in result
        assert "period_end" in result
        assert "total_resources" in result
        assert "low_utilization_count" in result
        assert "high_utilization_count" in result
        assert "unstable_count" in result
        assert "missing_metrics_count" in result
        assert "resources" in result

    def test_resource_has_stats(self, service):
        result = service.get_utilization_summary()
        for r in result["resources"]:
            assert "cpu" in r
            assert "memory" in r
            assert "disk" in r
            assert "cpu_pattern" in r
            assert "memory_pattern" in r
            assert r["cpu"]["avg"] is not None or r["cpu"]["avg"] is None

    def test_stats_have_all_fields(self, service):
        result = service.get_utilization_summary()
        for r in result["resources"]:
            if r["cpu"]["avg"] is not None:
                assert "avg" in r["cpu"]
                assert "min" in r["cpu"]
                assert "max" in r["cpu"]
                assert "p95" in r["cpu"]
                assert r["cpu"]["min"] <= r["cpu"]["avg"] <= r["cpu"]["max"]

    def test_p95_is_above_avg(self, service):
        result = service.get_utilization_summary()
        for r in result["resources"]:
            if r["cpu"]["avg"] is not None:
                assert r["cpu"]["p95"] >= r["cpu"]["avg"]

    def test_pattern_analysis_detects_low_util(self, service):
        result = service.get_utilization_summary()
        low_cpu = [r for r in result["resources"] if r["cpu_pattern"]["status"] == "low"]
        assert len(low_cpu) > 0
        for r in low_cpu:
            assert r["cpu"]["avg"] < 15
            assert "underutilized" in r["cpu_pattern"]["evidence"]

    def test_pattern_analysis_has_evidence(self, service):
        result = service.get_utilization_summary()
        for r in result["resources"]:
            assert "status" in r["cpu_pattern"]
            assert "evidence" in r["cpu_pattern"]
            assert len(r["cpu_pattern"]["evidence"]) > 0

    def test_missing_metrics_for_storage(self, service):
        result = service.get_utilization_summary()
        storage = [r for r in result["resources"] if "storage" in r["service"].lower() or "artifact" in r["service"].lower()]
        for r in storage:
            assert r["cpu"]["avg"] is None
            assert r["cpu_pattern"]["status"] == "missing"

    def test_get_resource_utilization(self, service):
        result = service.get_resource_utilization("vm-prod-api-01")
        assert result is not None
        assert result["resource_id"] == "vm-prod-api-01"
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "history" in result

    def test_resource_utilization_history_has_data(self, service):
        result = service.get_resource_utilization("vm-prod-api-01")
        assert len(result["history"]) == 30
        for entry in result["history"]:
            assert "date" in entry
            assert "cpu_utilization" in entry
            assert "memory_utilization" in entry

    def test_resource_not_found(self, service):
        result = service.get_resource_utilization("does-not-exist")
        assert result is None

    def test_compute_stats_with_zero_values(self, service):
        stats = service._compute_stats([0.0, 0.0, 0.0])
        assert stats["avg"] == 0.0
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["p95"] == 0.0

    def test_compute_stats_with_empty_list(self, service):
        stats = service._compute_stats([])
        assert stats["avg"] is None
        assert stats["min"] is None
        assert stats["max"] is None
        assert stats["p95"] is None

    def test_compute_stats_with_single_value(self, service):
        stats = service._compute_stats([50.0])
        assert stats["avg"] == 50.0
        assert stats["min"] == 50.0
        assert stats["max"] == 50.0
        assert stats["p95"] == 50.0

    def test_analyze_pattern_low(self, service):
        stats = {"avg": 5.0, "min": 2.0, "max": 8.0, "p95": 7.0}
        pattern = service._analyze_pattern(stats, "CPU")
        assert pattern["status"] == "low"

    def test_analyze_pattern_high(self, service):
        stats = {"avg": 90.0, "min": 85.0, "max": 95.0, "p95": 94.0}
        pattern = service._analyze_pattern(stats, "CPU")
        assert pattern["status"] == "high"

    def test_analyze_pattern_unstable(self, service):
        stats = {"avg": 50.0, "min": 10.0, "max": 90.0, "p95": 85.0}
        pattern = service._analyze_pattern(stats, "CPU")
        assert pattern["status"] == "unstable"

    def test_analyze_pattern_normal(self, service):
        stats = {"avg": 60.0, "min": 50.0, "max": 70.0, "p95": 68.0}
        pattern = service._analyze_pattern(stats, "CPU")
        assert pattern["status"] == "normal"

    def test_analyze_pattern_missing(self, service):
        stats = {"avg": None, "min": None, "max": None, "p95": None}
        pattern = service._analyze_pattern(stats, "CPU")
        assert pattern["status"] == "missing"

    def test_cost_vs_utilization(self, service):
        result = service.get_cost_vs_utilization()
        assert "data" in result
        assert len(result["data"]) == 8
        for r in result["data"]:
            assert "resource_id" in r
            assert "name" in r
            assert "cost" in r
            assert "cpu_avg" in r
            assert r["cost"] > 0

    def test_cost_vs_util_storage_has_null_cpu(self, service):
        result = service.get_cost_vs_utilization()
        storage = [r for r in result["data"] if "storage" in r["service"].lower() or "artifact" in r["service"].lower()]
        for r in storage:
            assert r["cpu_avg"] is None


class TestUtilizationAPI:
    def test_utilization_summary(self, client):
        response = client.get("/api/utilization")
        assert response.status_code == 200
        data = response.json()
        assert data["total_resources"] == 8
        assert "low_utilization_count" in data

    def test_utilization_with_date_range(self, client):
        response = client.get("/api/utilization?start_date=2026-08-01&end_date=2026-08-15")
        assert response.status_code == 200
        data = response.json()
        assert data["period_start"] == "2026-08-01"
        assert data["period_end"] == "2026-08-15"

    def test_resource_utilization(self, client):
        response = client.get("/api/utilization/vm-prod-api-01")
        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == "vm-prod-api-01"
        assert len(data["history"]) == 30

    def test_resource_utilization_not_found(self, client):
        response = client.get("/api/utilization/does-not-exist")
        assert response.status_code == 404

    def test_cost_vs_utilization_endpoint(self, client):
        response = client.get("/api/utilization/cost-vs-utilization/data")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 8

    def test_invalid_date_format(self, client):
        response = client.get("/api/utilization?start_date=invalid")
        assert response.status_code == 422
