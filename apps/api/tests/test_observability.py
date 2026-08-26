"""Tests for observability: metrics, SLI/SLO, alerts."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.observability.metrics import Metrics
from app.observability.sli import calculate_slis, get_slo_status, SLO_TARGETS
from app.observability.alerts import evaluate_alerts, ALERT_RULES
from app.observability.metrics import metrics as global_metrics


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_metrics():
    global_metrics.reset()
    yield
    global_metrics.reset()


class TestMetrics:
    def test_increment_counter(self):
        m = Metrics()
        m.increment("test_counter")
        assert m.get_counter("test_counter") == 1
        m.increment("test_counter", 5)
        assert m.get_counter("test_counter") == 6

    def test_counter_with_labels(self):
        m = Metrics()
        m.increment("requests", labels={"method": "GET", "status": "200"})
        m.increment("requests", labels={"method": "POST", "status": "200"})
        assert m.get_counter("requests", labels={"method": "GET", "status": "200"}) == 1
        assert m.get_counter("requests", labels={"method": "POST", "status": "200"}) == 1

    def test_observe_histogram(self):
        m = Metrics()
        m.observe("duration", 0.1)
        m.observe("duration", 0.2)
        m.observe("duration", 0.3)
        hist = m.get_histogram("duration")
        assert hist["count"] == 3
        assert hist["avg"] == 0.2

    def test_histogram_percentiles(self):
        m = Metrics()
        for i in range(100):
            m.observe("latency", float(i))
        hist = m.get_histogram("latency")
        assert hist["p50"] == 50.0
        assert hist["p95"] == 95.0
        assert hist["p99"] == 99.0

    def test_set_gauge(self):
        m = Metrics()
        m.set_gauge("freshness", 28800.0)
        assert m.get_gauge("freshness") == 28800.0
        m.set_gauge("freshness", 36000.0)
        assert m.get_gauge("freshness") == 36000.0

    def test_get_all(self):
        m = Metrics()
        m.increment("counter_a")
        m.observe("hist_a", 1.0)
        m.set_gauge("gauge_a", 5.0)
        result = m.get_all()
        assert "counters" in result
        assert "histograms" in result
        assert "gauges" in result

    def test_reset(self):
        m = Metrics()
        m.increment("test")
        m.reset()
        assert m.get_counter("test") == 0


class TestSLI:
    def test_sli_calculation(self):
        slis = calculate_slis()
        assert "api_availability" in slis
        assert "billing_data_freshness" in slis
        assert "recommendation_success_rate" in slis

    def test_sli_has_fields(self):
        slis = calculate_slis()
        for name, sli in slis.items():
            assert "current" in sli
            assert "target" in sli
            assert "unit" in sli
            assert "status" in sli
            assert sli["status"] in ["MET", "BREACHED"]

    def test_slo_status(self):
        status = get_slo_status()
        assert "overall_status" in status
        assert "slis" in status
        assert "slo_targets" in status
        assert status["overall_status"] in ["HEALTHY", "DEGRADED"]

    def test_slo_targets_defined(self):
        assert "api_availability" in SLO_TARGETS
        assert "billing_data_freshness" in SLO_TARGETS
        assert "recommendation_success_rate" in SLO_TARGETS
        assert SLO_TARGETS["api_availability"]["target"] == 99.5
        assert SLO_TARGETS["billing_data_freshness"]["target"] == 24.0
        assert SLO_TARGETS["recommendation_success_rate"]["target"] == 99.0


class TestAlerts:
    def test_no_alerts_by_default(self):
        alerts = evaluate_alerts()
        assert isinstance(alerts, list)

    def test_billing_stale_alert(self):
        global_metrics.set_gauge("billing_data_freshness_seconds", 140000)
        alerts = evaluate_alerts()
        stale_alerts = [a for a in alerts if a["name"] == "BillingDataStale"]
        assert len(stale_alerts) == 1
        assert stale_alerts[0]["severity"] == "WARNING"

    def test_billing_critical_alert(self):
        global_metrics.set_gauge("billing_data_freshness_seconds", 200000)
        alerts = evaluate_alerts()
        critical_alerts = [a for a in alerts if a["name"] == "BillingDataCritical"]
        assert len(critical_alerts) == 1
        assert critical_alerts[0]["severity"] == "CRITICAL"

    def test_recommendation_failure_alert(self):
        global_metrics.increment("recommendations_failed_total")
        alerts = evaluate_alerts()
        rec_alerts = [a for a in alerts if a["name"] == "RecommendationFailure"]
        assert len(rec_alerts) == 1

    def test_forecast_failure_alert(self):
        global_metrics.increment("forecast_failed_total")
        alerts = evaluate_alerts()
        fc_alerts = [a for a in alerts if a["name"] == "ForecastFailure"]
        assert len(fc_alerts) == 1

    def test_alert_rules_have_runbooks(self):
        for rule in ALERT_RULES:
            assert "runbook" in rule
            assert rule["runbook"].startswith("docs/runbooks/")


class TestObservabilityAPI:
    def test_metrics_endpoint(self, client):
        client.get("/health")
        response = client.get("/api/observability/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "counters" in data
        assert "histograms" in data
        assert "gauges" in data

    def test_slo_endpoint(self, client):
        response = client.get("/api/observability/slo")
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "slis" in data

    def test_alerts_endpoint(self, client):
        response = client.get("/api/observability/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "active_alerts" in data
        assert "total_active" in data
        assert "alert_rules" in data

    def test_metrics_middleware_tracks_requests(self, client):
        global_metrics.reset()
        client.get("/health")
        client.get("/health")
        client.get("/api/cost")
        all_m = global_metrics.get_all()
        total = sum(v for k, v in all_m["counters"].items() if k.startswith("http_requests_total"))
        assert total >= 3
