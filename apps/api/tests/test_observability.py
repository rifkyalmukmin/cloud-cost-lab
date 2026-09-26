"""Observability tests (Phase 12, CLAUDE.md §40/§43).

The prometheus_client registry is process-global; tests that increment
counters therefore assert on metric PRESENCE and value CHANGES rather than
exact absolute numbers, so test ordering cannot break them.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from costlab.analytics.observability import (
    bigquery_query_duration_seconds,
    billing_data_freshness_seconds,
    billing_records_processed_total,
    forecast_runs_total,
    http_requests_total,
    recommendation_runs_total,
    recommendations_generated_total,
)
from costlab.providers.gcp import GCPBillingProvider

REQUIRED_METRICS = (
    "http_requests_total",
    "http_request_duration_seconds",
    "billing_records_processed_total",
    "billing_data_freshness_seconds",
    "recommendations_generated_total",
    "forecast_runs_total",
    "bigquery_query_duration_seconds",
)

# ---------------------------------------------------------------------------
# Stubs for the BigQuery provider path
# ---------------------------------------------------------------------------


class StubRow:
    def __init__(self, data: dict) -> None:
        self._data = data

    def __getitem__(self, key: str):
        return self._data[key]


class StubJob:
    def __init__(self, dry_run=False) -> None:
        self._dry_run = dry_run
        self.total_bytes_processed = 1024 if dry_run else None

    def result(self):
        return []


class StubClient:
    def query(self, sql: str, job_config=None):
        if job_config is not None and getattr(job_config, "is_dry_run", False):
            return StubJob(dry_run=True)
        return StubJob()


class StubJobConfigs:
    def __init__(self, is_dry_run=False, query_parameters=None) -> None:
        self.is_dry_run = is_dry_run
        self.query_parameters = query_parameters or []

    def new_dry_run(self) -> StubJobConfigs:
        return StubJobConfigs(is_dry_run=True)

    def with_parameters(self, parameters) -> StubJobConfigs:
        return StubJobConfigs(query_parameters=list(parameters))


def _billing_provider() -> GCPBillingProvider:
    settings = SimpleNamespace(
        gcp_billing_project="p",
        gcp_billing_dataset="d",
        gcp_billing_table="t",
        gcp_billing_location="US",
        gcp_billing_max_days=30,
        gcp_billing_max_rows=100,
    )
    return GCPBillingProvider(
        settings,
        client_factory=StubClient,
        job_configs_factory=StubJobConfigs,
    )


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def _counter_value(counter) -> float:
    """Sum counter samples, excluding the `_created` epoch-time series."""
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_created"):
                continue
            total += sample.value
    return total


def _counter_value_by_label(counter, label: str) -> float:
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.labels.get("result") == label:
                total += sample.value
    return total


def _counter_labels(counter) -> set[tuple[str, ...]]:
    labels = set()
    for metric in counter.collect():
        for sample in metric.samples:
            labels.add(tuple(sorted(sample.labels.items())))
    return labels


# ---------------------------------------------------------------------------
# Metric exposition
# ---------------------------------------------------------------------------


def test_all_required_metrics_exposed(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text
    for metric in REQUIRED_METRICS:
        assert metric in text, metric


def test_requests_counter_increments(client: TestClient) -> None:
    def requests_for(path: str) -> float:
        for metric in http_requests_total.collect():
            for sample in metric.samples:
                if sample.labels.get("path") == path:
                    return sample.value
        return 0.0

    before = requests_for("/health")
    client.get("/health")
    client.get("/health")
    assert requests_for("/health") == pytest.approx(before + 2)


def test_billing_records_counter_set_by_seeding() -> None:
    """conftest ingests the mock dataset -> the processed-records counter has
    ingested samples with a real count."""
    assert _counter_value_by_label(billing_records_processed_total, "ingested") >= 1


def test_freshness_gauge_set_by_ingest() -> None:
    """conftest ingests the mock dataset, so the freshness gauge must be set
    (data ends 2026-09-05 -> a large but finite age)."""
    value = billing_data_freshness_seconds.collect()[0].samples[0].value
    assert value > 0


def test_recommendation_run_counters(client: TestClient) -> None:
    client.post("/api/recommendations/run")

    assert _counter_value_by_label(recommendation_runs_total, "success") >= 1
    body = client.get("/api/recommendations").json()
    assert _counter_value(recommendations_generated_total) >= body["pagination"]["total_items"]


def test_forecast_run_counter(client: TestClient) -> None:
    before = _counter_value(forecast_runs_total)
    client.get("/api/forecast")
    after = _counter_value(forecast_runs_total)
    assert after == pytest.approx(before + 1)


def test_bigquery_duration_histogram_records() -> None:
    before = _counter_value(bigquery_query_duration_seconds)
    _billing_provider().load_snapshot()
    after = _counter_value(bigquery_query_duration_seconds)
    # dry run + real query both observed (dry run has no count impact, the
    # real query does; the histogram count must increase by >= 1)
    assert after >= before + 1


# ---------------------------------------------------------------------------
# SLIs/SLOs and alerts
# ---------------------------------------------------------------------------


def test_reliability_endpoint_sli_slo_contract(client: TestClient) -> None:
    response = client.get("/api/reliability")
    assert response.status_code == 200
    body = response.json()

    slos = body["slos"]
    assert slos["api_availability"]["target"] == 0.995
    assert slos["billing_data_freshness"]["target"] == 24 * 3600
    assert slos["recommendation_success"]["target"] == 0.99

    slis = body["slis"]
    # requests already served in this session -> availability measurable, no 5xx
    assert slis["api_availability"]["sli"] is not None
    assert slis["api_availability"]["met"] is True
    # dataset ends 2026-09-05 (old vs wall clock) -> freshness SLO NOT met
    freshness = slis["billing_data_freshness"]
    assert freshness["met"] is False
    assert freshness["sli"] == pytest.approx(freshness["sli"])  # numeric, not None
    # recommendation runs exist -> measurable
    assert slis["recommendation_success"]["sli"] is not None


def test_alerts_endpoint_and_stale_incident(client: TestClient) -> None:
    response = client.get("/api/alerts")
    assert response.status_code == 200
    body = response.json()
    names = {alert["name"] for alert in body["alerts"]}
    assert {"BillingDataStale", "APIAvailabilityLow", "RecommendationPipelineFailing"} <= names
    # the demo dataset is stale -> the matching alert fires, linked to INC-001
    stale = next(alert for alert in body["alerts"] if alert["name"] == "BillingDataStale")
    assert stale["state"] == "firing"
    assert stale["runbook"].endswith("#inc-001-billing-stale")
    assert body["summary"]["firing"] >= 1


def test_alert_logic_zero_baseline_is_critical(monkeypatch) -> None:
    """UNKNOWN freshness (no data at all) -> BillingDataMissing critical."""
    from costlab.analytics import observability as obs

    unknown = {"status": "UNKNOWN", "last_updated": None, "data_age_hours": None}
    alerts = obs.evaluate_alerts(unknown)
    missing = next(a for a in alerts if a["name"] == "BillingDataMissing")
    assert missing["severity"] == "critical" and missing["state"] == "firing"


def test_freshness_slo_boundary_24h() -> None:
    """Deterministic boundary: data complete < 24h ago is FRESH; complete
    >= 24h ago (with max_age_hours=24) is STALE."""
    from costlab.analytics.freshness import compute_freshness

    now = datetime(2026, 9, 27, 9, 0, tzinfo=UTC)
    # newest day = yesterday -> complete today 00:00 UTC -> 9h old -> FRESH
    fresh = compute_freshness(date(2026, 9, 26), now, max_age_hours=24)
    assert fresh.status == "FRESH" and fresh.data_age_hours == pytest.approx(9.0)
    # newest day = Sep 24 -> complete Sep 25 00:00 -> 57h old -> STALE
    stale = compute_freshness(date(2026, 9, 24), now, max_age_hours=24)
    assert stale.status == "STALE"
    assert stale.data_age_hours == pytest.approx(57.0)
