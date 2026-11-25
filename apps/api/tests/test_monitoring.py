"""Tests for monitoring service and providers."""

from datetime import date, datetime
from unittest.mock import patch

import pytest
from app.main import app
from app.providers.gcp_monitoring import GCPMonitoringProvider, GCPMonitoringProviderError
from app.providers.mock_monitoring import MockMonitoringProvider
from app.providers.monitoring_base import MetricsFreshness
from app.providers.monitoring_factory import create_monitoring_provider
from app.services.monitoring_service import MonitoringService
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_provider():
    return MockMonitoringProvider()


@pytest.fixture
def service():
    return MonitoringService(provider=MockMonitoringProvider())


class TestMetricsFreshness:
    def test_fresh_status(self):
        f = MetricsFreshness(last_updated=datetime(2026, 8, 26, 11, 0, 0), status="FRESH")
        result = f.to_dict()
        assert result["status"] == "FRESH"
        assert result["data_age_hours"] == 1.0

    def test_stale_status(self):
        f = MetricsFreshness(last_updated=datetime(2026, 8, 24, 0, 0, 0), status="STALE")
        result = f.to_dict()
        assert result["status"] == "STALE"
        assert result["data_age_hours"] == 60.0

    def test_unknown_status(self):
        f = MetricsFreshness(status="UNKNOWN")
        result = f.to_dict()
        assert result["status"] == "UNKNOWN"
        assert result["last_updated"] is None
        assert result["data_age_hours"] is None


class TestMockMonitoringProvider:
    def test_is_available(self, mock_provider):
        assert mock_provider.is_available() is True

    def test_data_freshness(self, mock_provider):
        freshness = mock_provider.get_data_freshness()
        assert freshness.status == "FRESH"
        assert freshness.last_updated is not None

    def test_get_resource_metrics(self, mock_provider):
        metrics = mock_provider.get_resource_metrics("vm-prod-api-01")
        assert metrics is not None
        assert metrics["resource_id"] == "vm-prod-api-01"
        assert metrics["cpu_utilization"] is not None
        assert metrics["memory_utilization"] is not None
        assert len(metrics["cpu_utilization"]) == 30

    def test_resource_not_found(self, mock_provider):
        metrics = mock_provider.get_resource_metrics("nonexistent")
        assert metrics is None

    def test_storage_resource_no_cpu(self, mock_provider):
        metrics = mock_provider.get_resource_metrics("gcs-prod-assets")
        assert metrics is not None
        assert metrics["cpu_utilization"] is None
        assert metrics["memory_utilization"] is None
        assert metrics["disk_utilization"] is not None

    def test_idle_resource_zero_requests(self, mock_provider):
        metrics = mock_provider.get_resource_metrics("vm-idle-01")
        assert metrics is not None
        for point in metrics["request_count"]:
            assert point["value"] >= 0

    def test_get_all_resource_metrics(self, mock_provider):
        all_metrics = mock_provider.get_all_resource_metrics()
        assert len(all_metrics) == 8
        for m in all_metrics:
            assert "resource_id" in m
            assert "cpu_avg" in m
            assert "memory_avg" in m
            assert "observation_days" in m

    def test_custom_date_range(self, mock_provider):
        metrics = mock_provider.get_resource_metrics(
            "vm-prod-api-01",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
        )
        assert metrics is not None
        assert metrics["observation_days"] == 10
        assert len(metrics["cpu_utilization"]) == 10

    def test_missing_metrics_are_none(self, mock_provider):
        metrics = mock_provider.get_resource_metrics("gcs-prod-assets")
        assert metrics["connections"] is None


class TestGCPMonitoringProvider:
    def test_init(self):
        provider = GCPMonitoringProvider(project_id="test-project")
        assert provider.project_id == "test-project"

    def test_not_available_without_library(self):
        provider = GCPMonitoringProvider(project_id="test-project")
        assert provider.is_available() is False

    def test_freshness_unknown_without_client(self):
        provider = GCPMonitoringProvider(project_id="test-project")
        freshness = provider.get_data_freshness()
        assert freshness.status == "UNKNOWN"

    def test_get_client_raises_without_library(self):
        provider = GCPMonitoringProvider(project_id="test-project")
        with pytest.raises(GCPMonitoringProviderError, match="google-cloud-monitoring not installed"):
            provider._get_client()


class TestMonitoringFactory:
    @patch("app.providers.monitoring_factory.settings")
    def test_creates_mock_in_demo_mode(self, mock_settings):
        mock_settings.demo_mode = True
        provider = create_monitoring_provider()
        assert isinstance(provider, MockMonitoringProvider)

    @patch("app.providers.monitoring_factory.settings")
    def test_creates_gcp_when_configured(self, mock_settings):
        mock_settings.demo_mode = False
        mock_settings.gcp_billing_project = "test-project"
        provider = create_monitoring_provider()
        assert isinstance(provider, GCPMonitoringProvider)

    @patch("app.providers.monitoring_factory.settings")
    def test_raises_when_project_missing(self, mock_settings):
        mock_settings.demo_mode = False
        mock_settings.gcp_billing_project = None
        with pytest.raises(RuntimeError, match="GCP monitoring integration requires"):
            create_monitoring_provider()


class TestMonitoringService:
    def test_enriched_metrics(self, service):
        result = service.get_enriched_resource_metrics()
        assert "resources" in result
        assert "monitoring_freshness" in result
        assert len(result["resources"]) == 8

    def test_enriched_resource_has_cost(self, service):
        result = service.get_enriched_resource_metrics()
        for r in result["resources"]:
            assert "monthly_cost" in r
            assert r["monthly_cost"] > 0

    def test_enriched_resource_has_evidence_strength(self, service):
        result = service.get_enriched_resource_metrics()
        for r in result["resources"]:
            assert r["evidence_strength"] in ["STRONG", "MODERATE", "WEAK", "INSUFFICIENT"]

    def test_evidence_strength_strong_with_data(self, service):
        result = service.get_enriched_resource_metrics()
        vm = next(r for r in result["resources"] if r["resource_id"] == "vm-prod-api-01")
        assert vm["evidence_strength"] == "STRONG"

    def test_resource_detail_metrics(self, service):
        result = service.get_resource_detail_metrics("vm-prod-api-01")
        assert result is not None
        assert result["resource_id"] == "vm-prod-api-01"
        assert "time_series" in result
        assert "evidence_strength" in result
        assert "summary" in result

    def test_resource_detail_not_found(self, service):
        result = service.get_resource_detail_metrics("nonexistent")
        assert result is None

    def test_evidence_strength_insufficient_short_period(self, service):
        strength = service._assess_evidence_strength(
            {"cpu_avg": 50.0, "memory_avg": 40.0},
            observation_days=2,
        )
        assert strength == "INSUFFICIENT"

    def test_evidence_strength_weak_few_days(self, service):
        strength = service._assess_evidence_strength(
            {"cpu_avg": 50.0, "memory_avg": None, "disk_avg": None},
            observation_days=5,
        )
        assert strength == "WEAK"

    def test_evidence_strength_moderate(self, service):
        strength = service._assess_evidence_strength(
            {"cpu_avg": 50.0, "memory_avg": None, "disk_avg": None},
            observation_days=10,
        )
        assert strength == "MODERATE"

    def test_evidence_strength_strong(self, service):
        strength = service._assess_evidence_strength(
            {"cpu_avg": 50.0, "memory_avg": 40.0, "disk_avg": 30.0},
            observation_days=20,
        )
        assert strength == "STRONG"

    def test_evidence_strength_no_metrics(self, service):
        strength = service._assess_evidence_strength(
            {"cpu_avg": None, "memory_avg": None, "disk_avg": None},
            observation_days=30,
        )
        assert strength == "WEAK"


class TestMonitoringAPI:
    def test_get_enriched_metrics(self, client):
        response = client.get("/api/monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        assert "monitoring_freshness" in data
        assert len(data["resources"]) == 8

    def test_get_resource_metrics(self, client):
        response = client.get("/api/monitoring/vm-prod-api-01")
        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == "vm-prod-api-01"
        assert "time_series" in data

    def test_resource_not_found(self, client):
        response = client.get("/api/monitoring/nonexistent")
        assert response.status_code == 404
