"""Recommendation engine tests (Phase 5).

Boundary conditions come first (CPU 0 / 5 / 10 / 20 / null and friends) — a
recommendation that fires on the wrong side of a threshold is a false
positive, which is worse than silence. Dataset-driven tests then prove the
engine reproduces exactly the known findings on the committed mock data
(idle VM, two oversized VMs, two cost anomalies, nothing else) and that the
human-approval lifecycle behaves.

The rules never touch infrastructure: even `POST /run` only writes rows to
this application's database.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from costlab.analytics.utilization import UtilizationRow
from costlab.recommendations.base import Evidence, RecommendationDraft
from costlab.recommendations.engine import priority_label, priority_score
from costlab.recommendations.rules import (
    ANOMALY_BASELINE_DAYS,
    CostAnomalyRule,
    IdleComputeRule,
    OversizedComputeRule,
)
from costlab.schemas.cost import PeriodOut
from costlab.schemas.utilization import MetricStats

# ---------------------------------------------------------------------------
# Helpers — synthetic UtilizationRow/MetricStats for pure boundary tests
# ---------------------------------------------------------------------------


def _stats(
    avg: float,
    *,
    p95: float | None = None,
    stddev: float | None = 1.0,
    count: int = 30,
) -> MetricStats:
    return MetricStats(
        avg=avg,
        min=0.0,
        max=max(avg, p95 or avg),
        p95=p95 if p95 is not None else avg,
        stddev=stddev,
        sample_count=count,
    )


def _row(
    *,
    resource_id: str = "vm-test-1",
    resource_type: str = "vm_instance",
    cpu: MetricStats | None = None,
    mem: MetricStats | None = None,
    net_in: MetricStats | None = None,
    net_out: MetricStats | None = None,
    requests: MetricStats | None = None,
    machine_type: str | None = "e2-standard-4",
    environment: str = "development",
    cost: float | None = 5.0,
) -> UtilizationRow:
    metrics = {}
    for name, stats in (
        ("cpu_utilization", cpu),
        ("memory_utilization", mem),
        ("network_in_mb", net_in),
        ("network_out_mb", net_out),
        ("request_count", requests),
    ):
        if stats is not None:
            metrics[name] = stats
    return UtilizationRow(
        resource_id=resource_id,
        resource_name=resource_id,
        resource_type=resource_type,
        service_id="compute-engine",
        service_name="Compute Engine",
        project_id="cc-lab-test",
        project_name="Test Project",
        environment=environment,
        region="us-central1",
        machine_type=machine_type,
        window=PeriodOut(start=date(2026, 6, 1), end=date(2026, 9, 5)),
        metrics=metrics,
        missing_metrics=[name for name, stats in (("request_count", requests),) if stats is None],
        cost_in_window=cost,
        cost_credits_in_window=cost * 0.05 if cost else None,
        cost_net_in_window=cost * 0.95 if cost else None,
        signals=None,  # type: ignore[arg-type]  # not used by the rules
    )


class _Context:
    def __init__(self, rows: list[UtilizationRow]) -> None:
        self.utilization_rows = rows
        self.window = None


IDLE = IdleComputeRule()
OVERSIZED = OversizedComputeRule()


def _idle_draft(cpu: MetricStats | None, **kwargs) -> RecommendationDraft | None:
    net_in = kwargs.pop("net_in", None)
    net_out = kwargs.pop("net_out", None)
    if net_in is None:
        net_in = _stats(5.0)
    if net_out is None:
        net_out = _stats(5.0)
    rows = [_row(cpu=cpu, net_in=net_in, net_out=net_out, **kwargs)]
    drafts = IDLE.evaluate(None, _Context(rows))  # type: ignore[arg-type]
    return drafts[0] if drafts else None


def _oversized_drafts(cpu: MetricStats, mem: MetricStats, **kwargs) -> list[RecommendationDraft]:
    rows = [_row(cpu=cpu, mem=mem, **kwargs)]
    return OVERSIZED.evaluate(None, _Context(rows))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# IdleComputeRule — the CPU boundary ladder (0 / 5 / 10 / 20 / null)
# ---------------------------------------------------------------------------


def test_idle_cpu_boundary_ladder() -> None:
    # 0% is a real observation — confidently idle, not missing.
    draft = _idle_draft(_stats(0.0, p95=0.5))
    assert draft is not None and draft.rule_id == "idle_compute"
    # just under the threshold — idle
    assert _idle_draft(_stats(4.99, p95=5.0)) is not None
    # exactly at the threshold — NOT idle (strictly below)
    assert _idle_draft(_stats(5.0, p95=5.0)) is None
    # well above — never
    assert _idle_draft(_stats(10.0)) is None
    assert _idle_draft(_stats(20.0)) is None
    # null CPU — silence, never a guess
    assert _idle_draft(None) is None


def test_idle_burst_guard_p95() -> None:
    # low average but spiky P95 → NOT confidently idle (could be batch jobs)
    assert _idle_draft(_stats(3.0, p95=25.0)) is None
    # P95 exactly at the guard value passes (guard is "above the guard fails")
    assert _idle_draft(_stats(3.0, p95=20.0)) is not None


def test_idle_insufficient_samples() -> None:
    short = _stats(1.0, p95=2.0, count=6)  # one week is the minimum
    assert _idle_draft(short) is None
    assert _idle_draft(_stats(1.0, p95=2.0, count=7)) is not None


def test_idle_network_boundary() -> None:
    # combined 99.9 MB/day passes, 100.0 fails (strictly below)
    assert _idle_draft(_stats(2.0), net_in=_stats(49.95), net_out=_stats(49.95)) is not None
    assert _idle_draft(_stats(2.0), net_in=_stats(50.0), net_out=_stats(50.0)) is None


def test_idle_requires_cost_evidence() -> None:
    assert _idle_draft(_stats(1.0, p95=2.0), cost=None) is None
    assert _idle_draft(_stats(1.0, p95=2.0), cost=0.0) is None


def test_idle_saving_and_risk_by_environment() -> None:
    dev = _idle_draft(_stats(1.0, p95=2.0), cost=2.09, environment="development")
    assert dev is not None
    # dev: scheduling scenario keeps the VM ~40% of the time → 60% saved
    assert dev.potential_savings == pytest.approx(2.09 * 0.6, abs=0.01)
    assert dev.risk == "LOW"
    assert "Schedule" in dev.recommendation

    prod = _idle_draft(_stats(1.0, p95=2.0), cost=2.09, environment="production")
    assert prod is not None
    # non-dev: decommission scenario saves the full observed cost, risk higher
    assert prod.potential_savings == pytest.approx(2.09, abs=0.01)
    assert prod.risk == "MEDIUM"


def test_idle_confidence_needs_network_evidence() -> None:
    with_net = _idle_draft(_stats(1.0, p95=2.0))
    assert with_net is not None and with_net.confidence == "HIGH"


def test_oversized_cpu_boundary_ladder() -> None:
    mem = _stats(30.0)
    assert _oversized_drafts(_stats(0.0), mem)  # 0 → oversized if mem+stable ok
    assert _oversized_drafts(_stats(10.0), mem)
    assert _oversized_drafts(_stats(19.99), mem)
    # exactly 20 → NOT oversized (strictly below)
    assert not _oversized_drafts(_stats(20.0), mem)
    assert not _oversized_drafts(_stats(22.59), mem)  # the dataset's sandbox-dev VM


def test_oversized_memory_and_stability_guards() -> None:
    cpu = _stats(10.0)
    assert not _oversized_drafts(cpu, _stats(40.0))  # exactly 40 → no
    assert _oversized_drafts(cpu, _stats(39.99))
    # instability: stddev above 15 → the mean is meaningless
    assert not _oversized_drafts(_stats(10.0, stddev=15.01), _stats(30.0))
    assert _oversized_drafts(_stats(10.0, stddev=15.0), _stats(30.0))
    # undefined stddev → silence
    assert not _oversized_drafts(_stats(10.0, stddev=None), _stats(30.0))
    # P95 headroom guard: spikes would not survive a smaller shape
    assert not _oversized_drafts(_stats(10.0, p95=40.01), _stats(30.0))
    assert _oversized_drafts(_stats(10.0, p95=40.0), _stats(30.0))
    # not enough samples to judge
    assert not _oversized_drafts(_stats(10.0, count=13), _stats(30.0, count=13))


def test_oversized_proposes_one_step_down_and_uses_half_cost() -> None:
    drafts = _oversized_drafts(_stats(11.0), _stats(30.29), cost=7.43)
    assert len(drafts) == 1
    draft = drafts[0]
    assert "e2-standard-4" in draft.recommendation and "e2-standard-2" in draft.recommendation
    assert draft.potential_savings == pytest.approx(7.43 * 0.5, abs=0.01)
    assert draft.potential_cost == pytest.approx(7.43 * 0.5, abs=0.01)
    assert draft.savings_percentage == pytest.approx(50.0, abs=0.1)
    # oversized drafts declare they are superseded by an idle finding
    assert draft.suppressed_by == ["idle_compute"]


def test_oversized_skips_unknown_machine_type_and_non_vms() -> None:
    assert not _oversized_drafts(_stats(10.0), _stats(30.0), machine_type="db-custom-4-16384")
    assert not _oversized_drafts(_stats(10.0), _stats(30.0), machine_type=None)
    bucket = _row(
        resource_type="storage_bucket",
        machine_type=None,
        cpu=None,
        requests=_stats(5000.0, count=97),
    )
    assert OVERSIZED.evaluate(None, _Context([bucket])) == []  # type: ignore[arg-type]


def test_oversized_prod_risk_higher_than_staging() -> None:
    prod = _oversized_drafts(_stats(10.0), _stats(30.0), environment="production")
    assert prod[0].risk == "MEDIUM"
    staging = _oversized_drafts(_stats(10.0), _stats(30.0), environment="staging")
    assert staging[0].risk == "LOW"


# ---------------------------------------------------------------------------
# Priority model (project-specific heuristic)
# ---------------------------------------------------------------------------


def _draft(**overrides) -> RecommendationDraft:
    base = dict(
        rule_id="idle_compute",
        title="t",
        resource_id="r",
        resource_label="r",
        project_id="p",
        service_id="s",
        scope_key="r",
        problem="p",
        evidence=[Evidence("fact")],
        current_cost=10.0,
        potential_cost=4.0,
        potential_savings=6.0,
        savings_percentage=60.0,
        risk="LOW",
        confidence="HIGH",
        effort="LOW",
    )
    base.update(overrides)
    return RecommendationDraft(**base)


def test_priority_score_saturates_and_labels() -> None:
    assert priority_score(_draft(potential_savings=10.0)) == 100.0  # full marks
    assert priority_score(_draft(potential_savings=50.0)) == 100.0  # saturates
    assert priority_score(_draft(potential_savings=0.0)) == 60.0  # 25+20+15
    assert priority_label(100.0) == "HIGH"
    assert priority_label(70.0) == "HIGH"
    assert priority_label(69.9) == "MEDIUM"
    assert priority_label(45.0) == "MEDIUM"
    assert priority_label(44.9) == "LOW"


def test_priority_penalizes_risk_and_effort() -> None:
    best = priority_score(_draft(risk="LOW", effort="LOW", confidence="HIGH"))
    worst = priority_score(_draft(risk="HIGH", effort="HIGH", confidence="LOW"))
    assert best > worst


# ---------------------------------------------------------------------------
# CostAnomalyRule — noise floor and run boundaries (pure helper)
# ---------------------------------------------------------------------------


def _flat_series(days: int, value: float) -> list[tuple[date, float]]:
    start = date(2026, 1, 1)
    return [(start + timedelta(days=i), value) for i in range(days)]


def test_anomaly_spike_run_boundaries() -> None:
    rule = CostAnomalyRule()
    # flat series → nothing
    assert rule._spike_runs(_flat_series(40, 1.0)) == []

    # ratio boundary: exactly 1.3x baseline is NOT a spike (strictly above);
    # the absolute delta floor ($0.05) also suppresses tiny bills
    points = _flat_series(ANOMALY_BASELINE_DAYS + 5, 1.0)
    points.append((date(2026, 2, 15), 1.3))  # == baseline * 1.3
    assert rule._spike_runs(points) == []
    points[-1] = (date(2026, 2, 15), 1.34)  # above ratio but delta 0.34 >= 0.05 → 1-day run
    assert rule._spike_runs(points) == []  # a single day is not an incident

    # a 2-day run is still not an incident
    two_day = _flat_series(ANOMALY_BASELINE_DAYS + 2, 1.0)
    two_day += [(date(2026, 2, 15), 1.5), (date(2026, 2, 16), 1.5)]
    assert rule._spike_runs(two_day) == []

    # 3 consecutive days at 1.5x → one incident run with the exact days
    three_day = _flat_series(ANOMALY_BASELINE_DAYS + 3, 1.0)
    three_day += [(date(2026, 2, 15) + timedelta(days=i), 1.5) for i in range(3)]
    runs = rule._spike_runs(three_day)
    assert len(runs) == 1 and len(runs[0]) == 3
    assert runs[0][0][0] == date(2026, 2, 15) and runs[0][-1][0] == date(2026, 2, 17)

    # two separated incidents → two runs (continuous daily series)
    spaced = _flat_series(ANOMALY_BASELINE_DAYS + 7, 1.0)  # Jan 1..Jan 21
    for i in range(3):  # Feb 15-17 spike (calendar continues from Jan 21)
        spaced.append((date(2026, 1, 22) + timedelta(days=i), 1.6))
    spaced.append((date(2026, 1, 25), 1.0))  # 2 flat days break the run
    spaced.append((date(2026, 1, 26), 1.0))
    for i in range(3):  # second spike episode
        spaced.append((date(2026, 1, 27) + timedelta(days=i), 1.6))
    runs = rule._spike_runs(spaced)
    assert len(runs) == 2
    assert runs[0][-1][0] == date(2026, 1, 24) and runs[1][0][0] == date(2026, 1, 27)


# ---------------------------------------------------------------------------
# Dataset-driven engine + API behaviour
# ---------------------------------------------------------------------------


def test_run_generates_expected_findings(client: TestClient) -> None:
    response = client.post("/api/recommendations/run")
    assert response.status_code == 200
    body = client.get("/api/recommendations", params={"page_size": 100}).json()

    by_rule: dict[str, list[str]] = {}
    for item in body["items"]:
        by_rule.setdefault(item["rule_id"], []).append(
            item["resource_id"] or item["resource_label"]
        )

    # idle: exactly the known idle dev VM
    assert by_rule["idle_compute"] == ["vm-report-dev-1"]
    # oversized: the two low-CPU stable VMs; sandbox-dev (CPU 22.6%) excluded;
    # report-dev suppressed by the idle finding
    assert sorted(by_rule["oversized_compute"]) == ["vm-etl-staging-1", "vm-legacy-sandbox-1"]
    # no disk resources and no near-zero-traffic buckets in the dataset —
    # the rules stay silent instead of inventing findings
    assert by_rule.get("unused_disk", []) == []
    assert by_rule.get("storage_retention", []) == []
    # anomalies: the designed Compute spike episodes, nothing on tiny noisy series
    assert len(by_rule["cost_anomaly"]) == 2
    assert all("compute-engine" in label for label in by_rule["cost_anomaly"])
    # TOTAL: no false positives — nothing for healthy prod VMs, SQL, buckets
    assert body["pagination"]["total_items"] == 5


def test_every_recommendation_carries_full_evidence(client: TestClient) -> None:
    client.post("/api/recommendations/run")
    body = client.get("/api/recommendations", params={"page_size": 100}).json()
    for item in body["items"]:
        assert item["evidence"], item["rule_id"]
        assert item["problem"] and item["recommendation"]
        assert item["current_cost"] >= 0 and item["potential_cost"] >= 0
        assert item["potential_savings"] > 0
        # percentage consistent with the money fields
        expected = round(item["potential_savings"] / item["current_cost"] * 100, 1)
        assert item["savings_percentage"] == pytest.approx(expected, abs=0.15)
        assert item["risk"] in ("LOW", "MEDIUM", "HIGH")
        assert item["confidence"] in ("HIGH", "MEDIUM", "LOW")
        assert item["effort"] in ("LOW", "MEDIUM", "HIGH")
        assert item["priority"] == priority_label(item["priority_score"])
        # nothing here may run without a human sign-off
        assert item["approval_required"] is True
        assert item["status"] == "OPEN"


def test_idle_draft_not_duplicated_by_oversized(client: TestClient) -> None:
    client.post("/api/recommendations/run")
    body = client.get(
        "/api/recommendations", params={"resource_id": "vm-report-dev-1", "page_size": 100}
    ).json()
    assert [item["rule_id"] for item in body["items"]] == ["idle_compute"]


def test_anomaly_excess_is_evidence_backed(client: TestClient) -> None:
    client.post("/api/recommendations/run")
    body = client.get(
        "/api/recommendations", params={"rule_id": "cost_anomaly", "page_size": 100}
    ).json()
    for item in body["items"]:
        metrics = {e["metric"]: e["value"] for e in item["evidence"]}
        assert metrics["anomaly.excess"] == pytest.approx(item["potential_savings"], abs=0.01)
        assert metrics["anomaly.run_days"] >= 3
        assert item["resource_id"] is None  # project/service scoped finding
        assert item["window"] is not None


def test_list_filters_sort_and_pagination(client: TestClient) -> None:
    client.post("/api/recommendations/run")

    by_rule = client.get("/api/recommendations", params={"rule_id": "idle_compute"}).json()
    assert by_rule["pagination"]["total_items"] == 1

    by_risk = client.get("/api/recommendations", params={"risk": "HIGH"}).json()
    assert by_risk["items"] == []  # nothing is HIGH-risk in this dataset

    by_priority = client.get("/api/recommendations", params={"priority": "MEDIUM"}).json()
    assert by_priority["items"]
    assert all(i["priority"] == "MEDIUM" for i in by_priority["items"])

    # sort by savings: the biggest first (oversized e2-standard-4)
    by_savings = client.get("/api/recommendations", params={"sort": "savings"}).json()
    savings = [i["potential_savings"] for i in by_savings["items"]]
    assert savings == sorted(savings, reverse=True)

    # sort=recent works
    assert client.get("/api/recommendations", params={"sort": "recent"}).status_code == 200

    # pagination: pages disjoint, beyond-end empty
    page1 = client.get("/api/recommendations", params={"page": 1, "page_size": 2}).json()
    page2 = client.get("/api/recommendations", params={"page": 2, "page_size": 2}).json()
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2) and ids2
    assert client.get("/api/recommendations", params={"page": 99}).json()["items"] == []


def test_list_validation_errors(client: TestClient) -> None:
    client.post("/api/recommendations/run")
    for params in (
        {"status": "CHAOS"},
        {"risk": "extreme"},
        {"priority": "urgent"},
        {"sort": "vibes"},
        {"page": 0},
    ):
        assert client.get("/api/recommendations", params=params).status_code == 422


def test_detail_404_and_roundtrip(client: TestClient) -> None:
    client.post("/api/recommendations/run")
    missing = client.get("/api/recommendations/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["error"]["request_id"]

    listed = client.get("/api/recommendations", params={"rule_id": "idle_compute"}).json()
    rec_id = listed["items"][0]["id"]
    detail = client.get(f"/api/recommendations/{rec_id}").json()
    assert detail["id"] == rec_id
    assert detail["resource_id"] == "vm-report-dev-1"
    assert detail["resource_label"] == "report-dev-1"  # resource display name
    assert len(detail["evidence"]) >= 3


def test_approval_lifecycle_and_run_preserves_status(client: TestClient) -> None:
    client.post("/api/recommendations/run")
    listed = client.get("/api/recommendations", params={"rule_id": "idle_compute"}).json()
    rec_id = listed["items"][0]["id"]

    # OPEN -> APPROVED
    approved = client.post(f"/api/recommendations/{rec_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    # double-approve → 409 (only OPEN transitions)
    assert client.post(f"/api/recommendations/{rec_id}/approve").status_code == 409
    assert client.post(f"/api/recommendations/{rec_id}/reject").status_code == 409

    # a second OPEN recommendation -> REJECTED
    other = client.get("/api/recommendations", params={"rule_id": "oversized_compute"}).json()[
        "items"
    ][0]
    rejected = client.post(f"/api/recommendations/{other['id']}/reject")
    assert rejected.json()["status"] == "REJECTED"

    # a re-run must NOT reset human decisions on unchanged findings
    client.post("/api/recommendations/run")
    after = client.get(f"/api/recommendations/{rec_id}").json()
    assert after["status"] == "APPROVED"
    summary = client.get("/api/recommendations").json()["summary"]["by_status"]
    assert summary["APPROVED"] == 1 and summary["REJECTED"] == 1

    # status filter finds them
    approved_list = client.get("/api/recommendations", params={"status": "APPROVED"}).json()
    assert [i["id"] for i in approved_list["items"]] == [rec_id]


def test_run_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/recommendations/run").json()
    second = client.post("/api/recommendations/run").json()
    assert first["generated"] == second["generated"] == 5
    assert second["removed"] == 0
    total = client.get("/api/recommendations").json()["pagination"]["total_items"]
    assert total == 5  # no duplicates accumulate
