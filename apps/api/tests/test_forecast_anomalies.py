"""Forecasting & anomaly detection tests (Phase 7).

The required scenarios — insufficient data, zero baseline, missing values,
spike, normal trend, large spike — are tested as PURE functions on synthetic
series (no database), plus API-level tests against the committed dataset.

Forecast promises (§27): expected/range, never exact; a zero baseline must
not explode; insufficient data must not invent numbers. Anomaly promises
(§28): one-sided (increases only), noise-floored, z-score + rolling average,
severity/confidence always present, warm-up period never flagged.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from costlab.analytics.anomalies import BASELINE_DAYS
from costlab.analytics.forecasting import MIN_HISTORY_DAYS, build_forecast
from costlab.db.session import SessionLocal  # noqa: F401  (engine wiring reference)

MOCK_DIR = Path(__file__).resolve().parents[3] / "data" / "mock"


# ---------------------------------------------------------------------------
# Forecast — pure scenarios on synthetic series (bypass the DB by monkeypatching
# the series builder through build_forecast's internals is intrusive; instead
# test the numeric behaviour via the module helpers with direct series inputs)
# ---------------------------------------------------------------------------


def _series(values: list[float], start: date = date(2026, 1, 1)) -> list[tuple[date, float]]:
    return [(start + timedelta(days=i), v) for i, v in enumerate(values)]


def test_forecast_insufficient_data(monkeypatch) -> None:
    from costlab.analytics import forecasting

    monkeypatch.setattr(
        forecasting,
        "_daily_series",
        lambda session, filters: _series([1.0] * (MIN_HISTORY_DAYS - 1)),
    )
    result = build_forecast(None, forecasting.CostFilters(), 30)  # type: ignore[arg-type]
    assert result["sufficient_data"] is False
    assert result["forecast"] == []
    assert result["confidence"] is None
    assert result["totals"] is None
    assert "Insufficient data" in result["message"]


def test_forecast_zero_baseline(monkeypatch) -> None:
    from costlab.analytics import forecasting

    monkeypatch.setattr(forecasting, "_daily_series", lambda session, filters: _series([0.0] * 60))
    result = build_forecast(None, forecasting.CostFilters(), 30)  # type: ignore[arg-type]
    assert result["sufficient_data"] is True
    # zero history -> zero expected cost, and the maths must not explode
    assert all(point["expected"] == 0.0 for point in result["forecast"])
    assert all(point["lower_bound"] == 0.0 for point in result["forecast"])
    assert result["totals"]["expected_30d"] == 0.0
    assert result["confidence"] == "LOW"


def test_forecast_normal_flat_trend(monkeypatch) -> None:
    from costlab.analytics import forecasting

    monkeypatch.setattr(forecasting, "_daily_series", lambda session, filters: _series([2.0] * 60))
    result = build_forecast(None, forecasting.CostFilters(), 30)  # type: ignore[arg-type]
    points = result["forecast"]
    assert len(points) == 30
    # flat series: MA level == 2.0, linear slope 0 -> expected == 2.0 every day
    assert all(point["moving_average"] == 2.0 for point in points)
    assert all(point["expected"] == pytest.approx(2.0, abs=0.01) for point in points)
    assert result["trend"] == "stable"
    assert result["confidence"] == "HIGH"  # zero residual noise over 60 days
    # bounds collapse onto the expectation for a noiseless series
    assert all(
        point["lower_bound"] <= point["expected"] <= point["upper_bound"] for point in points
    )
    assert result["totals"]["expected_30d"] == pytest.approx(60.0, abs=0.1)


def test_forecast_increasing_trend_shows_in_slope(monkeypatch) -> None:
    from costlab.analytics import forecasting

    # steady ramp: 1.0 -> 3.0 over 60 days
    values = [1.0 + i * (2.0 / 59) for i in range(60)]
    monkeypatch.setattr(forecasting, "_daily_series", lambda session, filters: _series(values))
    result = build_forecast(None, forecasting.CostFilters(), 30)  # type: ignore[arg-type]
    assert result["trend"] == "increasing"
    assert result["methods"]["linear_trend"]["slope_per_day"] == pytest.approx(2.0 / 59, abs=1e-4)
    points = result["forecast"]
    # the blend keeps rising and ends above the flat MA baseline
    assert points[-1]["linear_trend"] > points[0]["linear_trend"]
    assert points[-1]["expected"] > result["methods"]["moving_average"]["level"]
    # bounds always bracket the expectation and costs never go negative
    assert all(
        0.0 <= point["lower_bound"] <= point["expected"] <= point["upper_bound"] for point in points
    )


def test_forecast_decreasing_trend(monkeypatch) -> None:
    from costlab.analytics import forecasting

    values = [3.0 - i * (2.0 / 59) for i in range(60)]
    monkeypatch.setattr(forecasting, "_daily_series", lambda session, filters: _series(values))
    result = build_forecast(None, forecasting.CostFilters(), 30)  # type: ignore[arg-type]
    assert result["trend"] == "decreasing"
    # the linear component keeps falling even below the MA level
    points = result["forecast"]
    assert points[-1]["linear_trend"] < result["methods"]["moving_average"]["level"]


def test_forecast_missing_values_filled_as_zero_days(monkeypatch) -> None:
    """Gaps in the series are zero-cost days: a flat 2.0/day series with a few
    missing days must still forecast near 2.0 (zeros dampen, not explode)."""
    from costlab.analytics import forecasting

    values = [2.0] * 60
    for gap in (5, 20, 40):
        values[gap] = 0.0  # the "missing day" becomes an explicit zero day
    monkeypatch.setattr(forecasting, "_daily_series", lambda session, filters: _series(values))
    result = build_forecast(None, forecasting.CostFilters(), 30)  # type: ignore[arg-type]
    assert result["sufficient_data"] is True
    assert result["forecast"][0]["expected"] == pytest.approx(2.0, abs=0.3)


# ---------------------------------------------------------------------------
# Anomalies — pure scenarios on synthetic grouped series
# ---------------------------------------------------------------------------


NAMES = {
    "projects": {"p1": "Project One"},
    "services": {"s1": "Service One"},
    "resources": {"r1": "resource-one"},
}


def _detect_with_series(monkeypatch, series: list[tuple[date, float]]):
    from costlab.analytics import anomalies as anomalies_mod

    monkeypatch.setattr(anomalies_mod, "_load_series", lambda session: {("p1", "s1", "r1"): series})
    monkeypatch.setattr(anomalies_mod, "_load_names", lambda session: NAMES)
    return anomalies_mod.detect_anomalies(None)  # type: ignore[arg-type]


def test_anomaly_normal_trend_has_no_findings(monkeypatch) -> None:
    # gentle noise around 2.0 — never beyond the noise floor
    values = [2.0, 2.05, 1.95, 2.02, 1.98, 2.0, 2.03, 1.97] * 10
    hits = _detect_with_series(monkeypatch, _series(values))
    assert hits == []


def test_anomaly_spike_detected_with_fields(monkeypatch) -> None:
    # small noise keeps the z-path live (stddev > 0) around a 2.0 baseline
    values = [2.0, 2.05, 1.95, 2.0] * 7 + [2.0, 2.0] + [2.0] * 2
    values = (values + [2.0] * 30)[:30]
    values[20] = 4.0  # a clear single-day spike (+100%)
    hits = _detect_with_series(monkeypatch, _series(values))
    assert len(hits) == 1
    hit = hits[0]
    assert hit.date == date(2026, 1, 1) + timedelta(days=20)
    assert hit.actual == 4.0
    assert hit.expected == pytest.approx(2.0, abs=0.05)
    assert hit.difference == pytest.approx(2.0, abs=0.05)
    assert hit.percentage_change == pytest.approx(100.0, abs=5.0)
    assert hit.z_score is not None and hit.z_score >= 2.0
    assert hit.severity == "HIGH"  # pct >= 100
    assert hit.baseline_samples == BASELINE_DAYS
    assert hit.resource_id == "r1" and hit.service_id == "s1" and hit.project_id == "p1"


def test_anomaly_large_spike_is_high_severity(monkeypatch) -> None:
    values = [2.0, 2.05, 1.95, 2.0] * 7 + [2.0, 2.0]
    values = (values + [2.0] * 30)[:30]
    values[25] = 20.0  # +900% — far beyond any band
    hits = _detect_with_series(monkeypatch, _series(values))
    assert len(hits) == 1
    assert hits[0].severity == "HIGH"
    assert hits[0].z_score is not None and hits[0].z_score >= 4.0
    assert hits[0].percentage_change == pytest.approx(900.0, abs=0.1)


def test_anomaly_zero_variance_baseline_step_change(monkeypatch) -> None:
    """A perfectly flat baseline makes z undefined (stddev 0); the step-change
    still surfaces through the percentage path — LOW severity, LOW confidence,
    z_score explicitly null (never fabricated)."""
    flat_then_jump = [1.0] * 44 + [2.0]
    hits = _detect_with_series(monkeypatch, _series(flat_then_jump))
    assert len(hits) == 1
    assert hits[0].z_score is None
    assert hits[0].severity == "LOW" and hits[0].confidence == "LOW"
    assert hits[0].percentage_change == pytest.approx(100.0, abs=0.1)


def test_anomaly_zero_cost_baseline_handling(monkeypatch) -> None:
    """All-zero baseline windows cannot express a percentage (expected <= 0)
    and are skipped — spend appearing from nothing is new spend, not a jump
    over a run-rate. Once the window MIXES zeros and spend, the appearance
    surfaces legitimately (a real, large percentage jump)."""
    values = [0.0] * 20 + [1.0] * 20
    hits = _detect_with_series(monkeypatch, _series(values))
    # the first cost days (all-zero baseline) are not flagged...
    first_day = date(2026, 1, 1) + timedelta(days=20)
    assert all(hit.date != first_day for hit in hits)
    # ...but the mixed-window days are, with a HIGH severity (+600%)
    assert hits and all(hit.expected > 0 for hit in hits)


def test_anomaly_insufficient_warmup_never_flagged(monkeypatch) -> None:
    """Within the first BASELINE_DAYS there is no baseline — even a huge value
    on day 2 is not an anomaly."""
    values = [2.0, 50.0] + [2.0] * (BASELINE_DAYS + 5)
    hits = _detect_with_series(monkeypatch, _series(values))
    assert all(hit.date.toordinal() - date(2026, 1, 1).toordinal() >= BASELINE_DAYS for hit in hits)


def test_anomaly_missing_values_use_available_days(monkeypatch) -> None:
    """Gaps (missing days) are simply absent — the baseline uses the last 14
    AVAILABLE days (not zero-filled), and a spike after gaps still detects."""
    start = date(2026, 1, 1)
    days = [start + timedelta(days=i) for i in range(40)]
    values = {day: 2.0 for day in days}
    del values[start + timedelta(days=10)]
    del values[start + timedelta(days=11)]
    values[start + timedelta(days=30)] = 6.0
    series = sorted(values.items())
    hits = _detect_with_series(monkeypatch, series)
    assert len(hits) == 1
    assert hits[0].date == start + timedelta(days=30)
    assert hits[0].baseline_samples == BASELINE_DAYS  # 14 available days used
    assert hits[0].expected == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Dataset + API level
# ---------------------------------------------------------------------------


def test_forecast_endpoint_shape_and_dates(client: TestClient) -> None:
    response = client.get("/api/forecast")
    assert response.status_code == 200
    body = response.json()
    assert body["sufficient_data"] is True
    assert len(body["forecast"]) == 30
    cost_rows = json.loads((MOCK_DIR / "cost.json").read_text(encoding="utf-8"))
    data_end = max(r["usage_date"] for r in cost_rows)
    assert (
        body["forecast"][0]["date"]
        == (date.fromisoformat(data_end) + timedelta(days=1)).isoformat()
    )
    assert body["confidence"] in ("LOW", "MEDIUM", "HIGH")
    assert body["interval"].startswith("80%")
    # bounds bracket expectations point by point
    for point in body["forecast"]:
        assert point["lower_bound"] <= point["expected"] <= point["upper_bound"]
    totals = body["totals"]
    assert totals["lower_bound_30d"] <= totals["expected_30d"] <= totals["upper_bound_30d"]
    # never presented as certain: the response carries method + interval metadata
    assert "moving_average" in body["methods"] and "linear_trend" in body["methods"]


def test_forecast_endpoint_horizon_validation(client: TestClient) -> None:
    assert client.get("/api/forecast", params={"horizon_days": 6}).status_code == 422
    assert client.get("/api/forecast", params={"horizon_days": 91}).status_code == 422
    short = client.get("/api/forecast", params={"horizon_days": 7})
    assert short.status_code == 200
    assert len(short.json()["forecast"]) == 7


def test_anomalies_endpoint_dataset_findings(client: TestClient) -> None:
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    body = response.json()
    # the designed spike week + September rise produce resource-level findings
    assert body["summary"]["total"] >= 10
    assert body["summary"]["by_severity"]["HIGH"] >= 1
    for item in body["items"]:
        assert item["actual"] > item["expected"]  # increases only
        assert item["difference"] == pytest.approx(item["actual"] - item["expected"], abs=0.01)
        assert item["percentage_change"] == pytest.approx(
            item["difference"] / item["expected"] * 100, abs=0.2
        )
        assert item["severity"] in ("LOW", "MEDIUM", "HIGH")
        assert item["confidence"] in ("LOW", "MEDIUM", "HIGH")
        assert item["service_name"] and item["project_name"]
    # sorted newest first
    dates = [item["date"] for item in body["items"]]
    assert dates == sorted(dates, reverse=True)


def test_anomalies_endpoint_filters_and_validation(client: TestClient) -> None:
    body = client.get("/api/anomalies").json()
    total = body["summary"]["total"]

    by_severity = client.get("/api/anomalies", params={"severity": "HIGH"}).json()
    assert by_severity["summary"]["total"] == body["summary"]["by_severity"]["HIGH"]
    assert all(i["severity"] == "HIGH" for i in by_severity["items"])

    by_service = client.get("/api/anomalies", params={"service": "compute-engine"}).json()
    assert by_service["summary"]["total"] <= total
    assert all(i["service_id"] == "compute-engine" for i in by_service["items"])

    by_resource = client.get("/api/anomalies", params={"resource_id": "vm-etl-staging-1"}).json()
    assert all(i["resource_id"] == "vm-etl-staging-1" for i in by_resource["items"])

    env = client.get("/api/anomalies", params={"environment": "staging"}).json()
    assert all(i["project_id"] == "cc-lab-shop-staging" for i in env["items"])

    # stricter z threshold shrinks the result
    strict = client.get("/api/anomalies", params={"min_z_score": 5.0}).json()
    assert strict["summary"]["total"] < total

    assert client.get("/api/anomalies", params={"severity": "extreme"}).status_code == 422
    assert client.get("/api/anomalies", params={"page": 0}).status_code == 422

    # pagination: pages disjoint
    p1 = client.get("/api/anomalies", params={"page": 1, "page_size": 5}).json()
    p2 = client.get("/api/anomalies", params={"page": 2, "page_size": 5}).json()
    ids1 = {(i["date"], i["resource_id"]) for i in p1["items"]}
    ids2 = {(i["date"], i["resource_id"]) for i in p2["items"]}
    assert ids1.isdisjoint(ids2)
