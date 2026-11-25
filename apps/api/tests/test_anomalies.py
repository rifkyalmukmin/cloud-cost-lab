"""Tests for anomaly detection."""

import pytest
from app.main import app
from app.services.anomaly_service import AnomalyService
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return AnomalyService()


class TestAnomalyService:
    def test_anomaly_detection_structure(self, service):
        result = service.detect_anomalies()
        assert "period_start" in result
        assert "period_end" in result
        assert "method" in result
        assert "threshold" in result
        assert "anomalies" in result
        assert "total_anomalies" in result

    def test_anomaly_has_required_fields(self, service):
        result = service.detect_anomalies()
        for anomaly in result["anomalies"]:
            assert "date" in anomaly
            assert "actual" in anomaly
            assert "expected" in anomaly
            assert "difference" in anomaly
            assert "percentage_change" in anomaly
            assert "z_score" in anomaly
            assert "severity" in anomaly
            assert "confidence" in anomaly

    def test_anomaly_has_attribution(self, service):
        result = service.detect_anomalies()
        for anomaly in result["anomalies"]:
            assert "top_service" in anomaly
            assert "top_project" in anomaly
            assert "top_resource" in anomaly

    def test_anomaly_severity(self, service):
        result = service.detect_anomalies()
        for anomaly in result["anomalies"]:
            assert anomaly["severity"] in ["MEDIUM", "HIGH"]

    def test_anomaly_confidence(self, service):
        result = service.detect_anomalies()
        for anomaly in result["anomalies"]:
            assert anomaly["confidence"] in ["HIGH", "MEDIUM", "LOW"]

    def test_anomaly_actual_greater_than_expected(self, service):
        result = service.detect_anomalies()
        for anomaly in result["anomalies"]:
            assert anomaly["actual"] > anomaly["expected"]

    def test_anomaly_difference_positive(self, service):
        result = service.detect_anomalies()
        for anomaly in result["anomalies"]:
            assert anomaly["difference"] > 0

    def test_anomaly_z_score_positive(self, service):
        result = service.detect_anomalies()
        for anomaly in result["anomalies"]:
            assert anomaly["z_score"] > 2.0


class TestAnomalyAPI:
    def test_get_anomalies(self, client):
        response = client.get("/api/anomalies")
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data
        assert "total_anomalies" in data

    def test_anomalies_with_lookback(self, client):
        response = client.get("/api/anomalies?lookback_days=14")
        assert response.status_code == 200
        data = response.json()
        assert data["lookback_days"] == 14

    def test_anomalies_with_date(self, client):
        response = client.get("/api/anomalies?reference_date=2026-08-20")
        assert response.status_code == 200
        data = response.json()
        assert data["period_end"] == "2026-08-20"
