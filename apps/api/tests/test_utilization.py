"""Utilization analytics tests (Phase 4).

Covers: aggregation (avg/min/max/stddev/P95 recomputed from the committed
dataset), P95 definition, null handling, zero values (a real 0 is kept,
missing is never 0), time-range filtering, missing metrics, evidence
signals, cost linkage, pagination, and the unknown-resource 404.

Evidence thresholds are project-specific heuristics (see
analytics/utilization.py); the classification function is unit-tested with
synthetic stats so high/unstable/zero behaviour is covered regardless of
what the mock dataset happens to contain.
"""

from __future__ import annotations

import json
import statistics
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from costlab.analytics.utilization import (
    HIGH_CPU_AVG,
    LOW_CPU_AVG,
    MIN_SAMPLES_FOR_UNSTABLE,
    UNSTABLE_CPU_STDDEV,
    classify_signals,
    expected_p95,
)
from costlab.schemas.utilization import MetricStats

MOCK_DIR = Path(__file__).resolve().parents[3] / "data" / "mock"
TOLERANCE = 1e-6


def _load(name: str) -> list[dict]:
    return json.loads((MOCK_DIR / name).read_text(encoding="utf-8"))


def _samples(resource_id: str, metric: str, start: str, end: str) -> list[Decimal]:
    """Non-null samples of one metric within [start, end] (what SQL aggregates)."""
    return [
        Decimal(str(row[metric]))
        for row in _load("usage.json")
        if row["resource_id"] == resource_id
        and row.get(metric) is not None
        and start <= row["usage_date"] <= end
    ]


def _round2(value: Decimal | float) -> float:
    return round(float(value), 2)


# ---------------------------------------------------------------------------
# Pure classification function (covers high / zero / missing without dataset)
# ---------------------------------------------------------------------------


def _stats(avg: float, stddev: float | None = None, count: int = 30) -> MetricStats:
    return MetricStats(avg=avg, min=0.0, max=100.0, p95=avg, stddev=stddev, sample_count=count)


def test_classification_low_high_unstable_and_missing() -> None:
    # CPU missing → all signals null (no signal is not the same as false)
    missing = classify_signals(None)
    assert (
        missing.low_utilization is None
        and missing.high_utilization is None
        and missing.unstable_utilization is None
    )

    low = classify_signals(_stats(4.2))
    assert low.low_utilization is True and low.high_utilization is False

    high = classify_signals(_stats(85.0))
    assert high.high_utilization is True and low.high_utilization is False

    boundary = classify_signals(_stats(LOW_CPU_AVG))
    assert boundary.low_utilization is False  # below the threshold, not on it

    # unstable: stddev above threshold with enough samples
    swing = classify_signals(_stats(40.0, stddev=UNSTABLE_CPU_STDDEV + 0.1))
    assert swing.unstable_utilization is True
    # …but not when stddev is small
    assert classify_signals(_stats(40.0, stddev=2.0)).unstable_utilization is False
    # …nor when there are too few samples to judge stability
    few = classify_signals(
        _stats(40.0, stddev=UNSTABLE_CPU_STDDEV + 10, count=MIN_SAMPLES_FOR_UNSTABLE - 1)
    )
    assert few.unstable_utilization is False
    # …nor with a single sample (stddev undefined)
    assert classify_signals(_stats(40.0, stddev=None, count=1)).unstable_utilization is False


def test_p95_matches_percentile_cont_definition() -> None:
    """P95 = linear interpolation at rank 0.95*(n-1), as SQL percentile_cont."""
    assert expected_p95([10.0]) == 10.0  # single sample
    assert expected_p95([0.0, 100.0]) == 95.0  # 0.95 * (2-1) = 0.95 → interpolated
    values = [float(i) for i in range(1, 101)]  # 1..100
    assert expected_p95(values) == 95.05


# ---------------------------------------------------------------------------
# List endpoint — aggregation against the committed dataset
# ---------------------------------------------------------------------------


def test_list_utilization_default_window_and_total(client: TestClient) -> None:
    response = client.get("/api/utilization")
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == 12
    # Defaults anchored to the data (2026-06-01 .. 2026-09-05), not the wall clock
    assert body["window"] == {"start": "2026-06-01", "end": "2026-09-05"}
    assert len(body["items"]) == 12
    for name in ("low_utilization", "high_utilization", "unstable_utilization", "missing_cpu"):
        assert name in body["signal_counts"]


def test_aggregation_matches_recomputation(client: TestClient) -> None:
    """avg/min/max/stddev/P95 for a compute resource match an independent
    recomputation over the same non-null samples."""
    rid = "vm-shop-api-prod-1"
    body = client.get("/api/utilization").json()
    item = next(i for i in body["items"] if i["resource_id"] == rid)

    for metric in ("cpu_utilization", "memory_utilization", "network_in_mb"):
        samples = _samples(rid, metric, "2026-06-01", "2026-09-05")
        stats = item["metrics"][metric]
        assert stats["sample_count"] == len(samples)
        assert stats["avg"] == pytest.approx(_round2(sum(samples) / len(samples)))
        assert stats["min"] == pytest.approx(_round2(min(samples)))
        assert stats["max"] == pytest.approx(_round2(max(samples)))
        assert stats["stddev"] == pytest.approx(_round2(statistics.stdev(samples)))
        assert stats["p95"] == pytest.approx(expected_p95(samples))


def test_p95_endpoint_matches_dataset(client: TestClient) -> None:
    """P95 from the API equals the percentile_cont definition on the dataset."""
    rid = "vm-shop-api-prod-2"
    body = client.get("/api/utilization").json()
    item = next(i for i in body["items"] if i["resource_id"] == rid)
    cpu_samples = _samples(rid, "cpu_utilization", "2026-06-01", "2026-09-05")
    assert item["metrics"]["cpu_utilization"]["p95"] == pytest.approx(expected_p95(cpu_samples))


def test_zero_values_are_present_not_missing(client: TestClient) -> None:
    """A metric observed as 0 is a real zero: it stays in the stats (avg/min
    include it) and is NOT reported as missing."""
    usage_rows = _load("usage.json")
    zero_rows = [r for r in usage_rows if r.get("cpu_utilization") == 0]
    assert zero_rows, "dataset is expected to contain at least one zero CPU sample"
    rid = zero_rows[0]["resource_id"]

    body = client.get("/api/utilization").json()
    item = next(i for i in body["items"] if i["resource_id"] == rid)
    assert "cpu_utilization" not in item["missing_metrics"]
    stats = item["metrics"]["cpu_utilization"]
    assert stats["min"] == 0.0
    samples = _samples(rid, "cpu_utilization", "2026-06-01", "2026-09-05")
    assert stats["avg"] == pytest.approx(_round2(sum(samples) / len(samples)))


def test_missing_metrics_and_nulls(client: TestClient) -> None:
    """Storage/registry resources have no compute metrics; latency exists in
    the model but has no samples anywhere — both surface as missing, never 0."""
    body = client.get("/api/utilization").json()
    by_id = {i["resource_id"]: i for i in body["items"]}

    bucket = by_id["gcs-shop-assets-prod"]
    assert "cpu_utilization" in bucket["missing_metrics"]
    assert "memory_utilization" in bucket["missing_metrics"]
    assert "latency_ms" in bucket["missing_metrics"]
    assert "cpu_utilization" not in bucket["metrics"]
    assert bucket["avg_cpu"] is None
    assert bucket["signals"] == {
        "low_utilization": None,
        "high_utilization": None,
        "unstable_utilization": None,
    }
    # …while its network/request metrics are present with real sample counts
    assert bucket["metrics"]["request_count"]["sample_count"] == 97

    # latency_ms has no samples for ANY resource (null column in the dataset)
    for item in body["items"]:
        assert "latency_ms" in item["missing_metrics"]
        assert "latency_ms" not in item["metrics"]

    # VMs have no request_count samples → missing for them
    vm = by_id["vm-shop-api-prod-1"]
    assert "request_count" in vm["missing_metrics"]


def test_items_sorted_by_avg_cpu_nulls_last(client: TestClient) -> None:
    body = client.get("/api/utilization").json()
    avg_cpus = [i["avg_cpu"] for i in body["items"]]
    present = [c for c in avg_cpus if c is not None]
    assert present == sorted(present, reverse=True)
    assert avg_cpus[len(present) :] == [None] * (len(avg_cpus) - len(present))


def test_signal_counts_cover_full_filtered_set(client: TestClient) -> None:
    """Counts must describe ALL filtered resources, not just the current page."""
    usage_rows = _load("usage.json")
    expected_low = 0
    expected_missing_cpu = 0
    for rid in {r["resource_id"] for r in usage_rows}:
        samples = _samples(rid, "cpu_utilization", "2026-06-01", "2026-09-05")
        if not samples:
            expected_missing_cpu += 1
        elif sum(samples) / len(samples) < LOW_CPU_AVG:
            expected_low += 1

    body = client.get("/api/utilization", params={"page_size": 5}).json()
    assert body["pagination"]["total_pages"] > 1
    assert body["signal_counts"]["low_utilization"] == expected_low
    assert body["signal_counts"]["missing_cpu"] == expected_missing_cpu
    assert body["signal_counts"]["high_utilization"] == 0  # max CPU in dataset is ~50%
    # counts identical on every page (they cover the full set)
    page2 = client.get("/api/utilization", params={"page_size": 5, "page": 2}).json()
    assert page2["signal_counts"] == body["signal_counts"]

    # and the dataset's idle dev VM really is flagged low
    full = client.get("/api/utilization").json()
    idle = next(i for i in full["items"] if i["resource_id"] == "vm-report-dev-1")
    assert idle["signals"]["low_utilization"] is True
    assert idle["signals"]["high_utilization"] is False


def test_cost_linked_to_same_window(client: TestClient) -> None:
    """Cost in the response is the cost of the SAME window as the stats."""
    rid = "vm-shop-api-prod-1"
    cost_rows = _load("cost.json")
    expected = round(
        float(
            sum(
                Decimal(str(r["cost"]))
                for r in cost_rows
                if r["resource_id"] == rid and "2026-06-01" <= r["usage_date"] <= "2026-09-05"
            )
        ),
        4,
    )
    body = client.get("/api/utilization").json()
    item = next(i for i in body["items"] if i["resource_id"] == rid)
    assert item["cost_in_window"] == pytest.approx(expected)
    assert item["cost_net_in_window"] < item["cost_in_window"]  # credits reduce net

    # a shorter window links to the smaller cost of exactly that window
    ranged = client.get(
        "/api/utilization",
        params={"start_date": "2026-08-01", "end_date": "2026-08-07"},
    ).json()
    ranged_item = next(i for i in ranged["items"] if i["resource_id"] == rid)
    expected_ranged = round(
        float(
            sum(
                Decimal(str(r["cost"]))
                for r in cost_rows
                if r["resource_id"] == rid and "2026-08-01" <= r["usage_date"] <= "2026-08-07"
            )
        ),
        4,
    )
    assert ranged_item["cost_in_window"] == pytest.approx(expected_ranged)
    assert ranged_item["window"] == {"start": "2026-08-01", "end": "2026-08-07"}


def test_time_range_narrows_stats(client: TestClient) -> None:
    """Stats inside an explicit sub-window equal the recomputation over it."""
    rid = "vm-etl-staging-1"
    body = client.get(
        "/api/utilization",
        params={"start_date": "2026-08-01", "end_date": "2026-08-07"},
    ).json()
    item = next(i for i in body["items"] if i["resource_id"] == rid)
    samples = _samples(rid, "cpu_utilization", "2026-08-01", "2026-08-07")
    assert item["metrics"]["cpu_utilization"]["sample_count"] == 7
    assert item["metrics"]["cpu_utilization"]["avg"] == pytest.approx(
        _round2(sum(samples) / len(samples))
    )


def test_filters_narrow_utilization_set(client: TestClient) -> None:
    by_project = client.get(
        "/api/utilization", params={"project_id": "cc-lab-shop-prod", "page_size": 100}
    ).json()
    assert by_project["pagination"]["total_items"] == 6
    assert all(i["project_id"] == "cc-lab-shop-prod" for i in by_project["items"])

    by_service = client.get(
        "/api/utilization", params={"service": "cloud-storage", "page_size": 100}
    ).json()
    assert by_service["pagination"]["total_items"] == 2

    by_env = client.get(
        "/api/utilization", params={"environment": "development", "page_size": 100}
    ).json()
    assert by_env["pagination"]["total_items"] == 3


def test_empty_result_and_pagination(client: TestClient) -> None:
    empty = client.get("/api/utilization", params={"project_id": "no-such-project"}).json()
    assert empty["items"] == []
    assert empty["pagination"]["total_items"] == 0
    assert empty["window"] is not None  # window still resolves from the data
    assert empty["signal_counts"]["low_utilization"] == 0

    page1 = client.get("/api/utilization", params={"page": 1, "page_size": 5}).json()
    page2 = client.get("/api/utilization", params={"page": 2, "page_size": 5}).json()
    assert page1["pagination"]["total_pages"] == 3
    ids1 = {i["resource_id"] for i in page1["items"]}
    ids2 = {i["resource_id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)
    assert client.get("/api/utilization", params={"page": 99}).json()["items"] == []
    assert client.get("/api/utilization", params={"page": 0}).status_code == 422


def test_invalid_time_range_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/utilization", params={"start_date": "2026-08-07", "end_date": "2026-08-01"}
    )
    assert response.status_code == 422
    assert client.get("/api/utilization", params={"environment": "chaos"}).status_code == 422


# ---------------------------------------------------------------------------
# Detail endpoint
# ---------------------------------------------------------------------------


def test_utilization_detail_series_and_stats(client: TestClient) -> None:
    response = client.get("/api/utilization/vm-shop-api-prod-1")
    assert response.status_code == 200
    detail = response.json()
    assert detail["resource_id"] == "vm-shop-api-prod-1"
    assert detail["machine_type"] == "e2-standard-2"
    assert detail["window"] == {"start": "2026-06-01", "end": "2026-09-05"}
    assert len(detail["series"]) == 97
    dates = [point["date"] for point in detail["series"]]
    assert dates == sorted(dates)
    assert dates[0] == "2026-06-01" and dates[-1] == "2026-09-05"
    # series agrees with the aggregate (max of series == max of stats)
    cpu_max_series = max(point["cpu_utilization"] for point in detail["series"])
    assert detail["metrics"]["cpu_utilization"]["max"] == pytest.approx(cpu_max_series)
    # explicit window narrows the series as well
    ranged = client.get(
        "/api/utilization/vm-shop-api-prod-1",
        params={"start_date": "2026-08-01", "end_date": "2026-08-07"},
    ).json()
    assert len(ranged["series"]) == 7
    assert ranged["window"] == {"start": "2026-08-01", "end": "2026-08-07"}


def test_utilization_detail_missing_metrics(client: TestClient) -> None:
    detail = client.get("/api/utilization/gcs-shop-assets-prod").json()
    assert "cpu_utilization" in detail["missing_metrics"]
    assert "latency_ms" in detail["missing_metrics"]
    assert detail["metrics"]["request_count"]["sample_count"] == 97
    assert detail["signals"]["low_utilization"] is None
    assert len(detail["series"]) == 97  # series rows exist even without CPU
    assert all(point["cpu_utilization"] is None for point in detail["series"])


def test_utilization_detail_unknown_resource_404(client: TestClient) -> None:
    response = client.get("/api/utilization/vm-does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "http_error"
    assert "vm-does-not-exist" in error["message"]
    assert error["request_id"]


def test_high_cpu_threshold_constant_documented() -> None:
    """Guard the heuristic values the docs promise."""
    assert LOW_CPU_AVG == 20.0
    assert HIGH_CPU_AVG == 80.0


def test_invalid_p95_guard() -> None:
    with pytest.raises(ValueError):
        expected_p95([])
