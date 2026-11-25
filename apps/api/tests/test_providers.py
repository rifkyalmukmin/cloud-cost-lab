"""Tests for billing data providers."""

from datetime import date, datetime
from unittest.mock import patch

import pytest
from app.main import app
from app.providers.base import DataFreshness
from app.providers.factory import create_billing_provider
from app.providers.gcp_provider import GCPBillingProvider, GCPBillingProviderError
from app.providers.mock_provider import MockBillingProvider
from app.services.cost_service import CostService
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


class TestDataFreshness:
    def test_fresh_status(self):
        freshness = DataFreshness(
            last_updated=datetime(2026, 8, 26, 4, 0, 0),
            status="FRESH",
        )
        result = freshness.to_dict()
        assert result["status"] == "FRESH"
        assert result["last_updated"] == "2026-08-26T04:00:00"
        assert result["data_age_hours"] == 8.0

    def test_stale_status(self):
        freshness = DataFreshness(
            last_updated=datetime(2026, 8, 24, 4, 0, 0),
            status="STALE",
        )
        result = freshness.to_dict()
        assert result["status"] == "STALE"
        assert result["data_age_hours"] == 56.0

    def test_unknown_status_no_timestamp(self):
        freshness = DataFreshness(status="UNKNOWN")
        result = freshness.to_dict()
        assert result["status"] == "UNKNOWN"
        assert result["last_updated"] is None
        assert result["data_age_hours"] is None


class TestMockBillingProvider:
    def test_is_available(self):
        provider = MockBillingProvider()
        assert provider.is_available() is True

    def test_get_cost_records(self):
        provider = MockBillingProvider()
        records = provider.get_cost_records(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )
        assert len(records) > 0
        for r in records:
            assert "project_id" in r
            assert "service_name" in r
            assert "cost" in r
            assert "net_cost" in r
            assert "usage_date" in r

    def test_get_cost_records_default_dates(self):
        provider = MockBillingProvider()
        records = provider.get_cost_records()
        assert len(records) > 0

    def test_get_cost_records_empty_range(self):
        provider = MockBillingProvider()
        records = provider.get_cost_records(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 1),
        )
        # Mock data should handle any date range (generates data for requested range)
        assert isinstance(records, list)

    def test_data_freshness(self):
        provider = MockBillingProvider()
        freshness = provider.get_data_freshness()
        assert freshness.status == "FRESH"
        assert freshness.last_updated is not None

    def test_deterministic_results(self):
        provider = MockBillingProvider()
        r1 = provider.get_cost_records(date(2026, 8, 1), date(2026, 8, 5))
        r2 = provider.get_cost_records(date(2026, 8, 1), date(2026, 8, 5))
        assert r1 == r2


class TestGCPBillingProvider:
    def test_init(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="gcp_billing_export_v1_TEST",
        )
        assert provider.project == "test-project"
        assert provider.dataset == "billing_export"
        assert provider.table == "gcp_billing_export_v1_TEST"

    def test_table_ref(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="gcp_billing_export_v1_TEST",
        )
        assert provider.table_ref == "`test-project.billing_export.gcp_billing_export_v1_TEST`"

    def test_not_available_without_library(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="test_table",
        )
        assert provider.is_available() is False

    def test_get_client_raises_without_library(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="test_table",
        )
        with pytest.raises(GCPBillingProviderError, match="google-cloud-bigquery not installed"):
            provider._get_client()

    def test_get_cost_records_raises_without_library(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="test_table",
        )
        with pytest.raises(GCPBillingProviderError):
            provider.get_cost_records()

    def test_data_freshness_unknown_without_client(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="test_table",
        )
        freshness = provider.get_data_freshness()
        assert freshness.status == "UNKNOWN"

    def test_rejects_unsafe_identifier(self):
        with pytest.raises(GCPBillingProviderError):
            GCPBillingProvider(project="proj`;drop", dataset="billing_export", table="test_table")

    def test_max_bytes_billed_is_bounded(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="test_table",
        )
        assert provider.MAX_BYTES_BILLED == 500 * 1024 * 1024

    def test_max_query_days_enforced(self):
        provider = GCPBillingProvider(
            project="test-project",
            dataset="billing_export",
            table="test_table",
        )
        assert provider.MAX_QUERY_DAYS == 90


class TestProviderFactory:
    @patch("app.providers.factory.settings")
    def test_creates_mock_when_demo_mode(self, mock_settings):
        mock_settings.demo_mode = True
        provider = create_billing_provider()
        assert isinstance(provider, MockBillingProvider)

    @patch("app.providers.factory.settings")
    def test_raises_when_gcp_config_missing(self, mock_settings):
        mock_settings.demo_mode = False
        mock_settings.gcp_billing_project = None
        mock_settings.gcp_billing_dataset = None
        mock_settings.gcp_billing_table = None
        with pytest.raises(RuntimeError, match="GCP billing integration requires"):
            create_billing_provider()

    @patch("app.providers.factory.settings")
    def test_creates_gcp_when_configured(self, mock_settings):
        mock_settings.demo_mode = False
        mock_settings.gcp_billing_project = "test-project"
        mock_settings.gcp_billing_dataset = "billing_export"
        mock_settings.gcp_billing_table = "gcp_billing_export_v1_TEST"
        provider = create_billing_provider()
        assert isinstance(provider, GCPBillingProvider)


class TestCostServiceWithProvider:
    def test_uses_mock_provider_by_default(self):
        service = CostService()
        assert isinstance(service.provider, MockBillingProvider)

    def test_can_inject_provider(self):
        provider = MockBillingProvider()
        service = CostService(provider=provider)
        assert service.provider is provider

    def test_summary_includes_freshness_status(self):
        service = CostService(provider=MockBillingProvider())
        summary = service.get_summary()
        assert "freshness_status" in summary
        assert summary["freshness_status"] == "FRESH"

    def test_get_data_freshness(self):
        service = CostService(provider=MockBillingProvider())
        freshness = service.get_data_freshness()
        assert "status" in freshness
        assert "last_updated" in freshness
        assert "data_age_hours" in freshness


class TestDataFreshnessAPI:
    def test_data_freshness_endpoint(self, client):
        response = client.get("/data-freshness")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "last_updated" in data
        assert data["status"] == "FRESH"

    def test_ready_endpoint_with_provider(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["provider"] == "mock"
        assert data["data_loaded"] is True
