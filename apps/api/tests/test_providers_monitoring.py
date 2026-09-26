"""GCP Monitoring provider + recommendation-strengthening tests (Phase 9).

The Cloud Monitoring client is stubbed — no network, no credentials. Covered
(required): provider failure, missing metrics, stale metrics, zero metrics;
plus valid multi-metric mapping, unit scaling, and the evidence rule that a
resource with active traffic or open connections is NEVER recommended as idle
regardless of cost.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from costlab.analytics.utilization import UtilizationRow
from costlab.providers.base import EmptyMonitoringProvider, MonitoringDataProvider
from costlab.providers.mock import MockMonitoringProvider
from costlab.providers.monitoring import GCPMonitoringError, GCPMonitoringProvider
from costlab.recommendations.rules import IdleComputeRule

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


def _settings(**overrides) -> SimpleNamespace:
    base = dict(
        gcp_monitoring_project="learn-cloud-gcp-506920",
        gcp_monitoring_max_days=30,
        gcp_monitoring_max_age_days=7,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _fake_runner(
    per_metric: dict[str, dict[str, dict[date, float]]] | None = None,
    error: Exception | None = None,
):
    """A stub query runner: per_metric maps metric key -> resource -> samples."""

    def runner(metric, start: date, end: date):
        if error is not None:
            raise error
        return per_metric.get(metric.key, {})

    return runner


# ---------------------------------------------------------------------------
# Valid mapping
# ---------------------------------------------------------------------------


def test_valid_monitoring_response_maps_all_metrics() -> None:
    day2 = datetime.now(UTC).date() - timedelta(days=1)
    day1 = day2 - timedelta(days=1)
    runner = _fake_runner(
        {
            "cpu_utilization": {"vm-1": {day1: 0.341, day2: 0.412}},  # 0-1 scale
            "memory_utilization": {"vm-1": {day1: 54.0, day2: 52.0}},
            "disk_utilization": {"vm-1": {day1: 30.0, day2: 31.0}},
            # cumulative counter in BYTES, like the real API
            "network_in_mb": {"vm-1": {day1: 2000.0 * 1024 * 1024, day2: 2100.0 * 1024 * 1024}},
            "network_out_mb": {"vm-1": {day1: 3000.0 * 1024 * 1024, day2: 3100.0 * 1024 * 1024}},
            "connections": {"sql-1": {day1: 12, day2: 9}},
        }
    )
    provider = GCPMonitoringProvider(_settings(), query_runner=runner)
    records = provider.load_usage()

    # two resources, two days each
    assert len(records) == 4
    vm_day1 = next(r for r in records if r.resource_id == "vm-1" and r.usage_date == day1)
    # CPU unit-scaled 0-1 -> percent
    assert vm_day1.cpu_utilization == pytest.approx(34.1)
    assert vm_day1.memory_utilization == 54.0
    assert vm_day1.disk_utilization == 30.0
    assert vm_day1.network_in_mb == 2000.0
    assert vm_day1.request_count is None  # no series for this metric
    # connections metric lands on the SQL resource
    sql_day1 = next(r for r in records if r.resource_id == "sql-1" and r.usage_date == day1)
    assert sql_day1.connections == 12
    assert sql_day1.cpu_utilization is None  # no CPU series for Cloud SQL


def test_missing_metrics_are_null_never_zero() -> None:
    """A resource with only a CPU series must show every other metric as None —
    missing data is never turned into a fabricated 0."""
    day = datetime.now(UTC).date() - timedelta(days=1)
    runner = _fake_runner({"cpu_utilization": {"vm-1": {day: 0.5}}})
    records = GCPMonitoringProvider(_settings(), query_runner=runner).load_usage()
    record = records[0]
    assert record.cpu_utilization == 50.0
    assert record.memory_utilization is None
    assert record.disk_utilization is None
    assert record.network_in_mb is None
    assert record.connections is None
    assert record.request_count is None


def test_zero_metrics_are_kept_as_real_zeros() -> None:
    """An observed 0 is an observation (idle night, no traffic) — it must land
    in the record as 0, not be dropped or reported as missing."""
    day = datetime.now(UTC).date() - timedelta(days=1)
    runner = _fake_runner(
        {
            "cpu_utilization": {"vm-1": {day: 0.0}},
            "request_count": {"lb-1": {day: 0.0}},
        }
    )
    records = GCPMonitoringProvider(_settings(), query_runner=runner).load_usage()
    cpu = next(r for r in records if r.resource_id == "vm-1")
    assert cpu.cpu_utilization == 0.0
    requests = next(r for r in records if r.resource_id == "lb-1")
    assert requests.request_count == 0


def test_stale_metrics_are_dropped_not_ingested() -> None:
    """A series whose newest sample is older than max_age_days is stale: it is
    dropped with a log line instead of being ingested as current utilization
    (SRE honesty — stale metrics must not back a 'healthy' story)."""
    fresh_day = datetime.now(UTC).date() - timedelta(days=1)
    stale_day = datetime.now(UTC).date() - timedelta(days=30)
    runner = _fake_runner(
        {
            "cpu_utilization": {
                "vm-fresh": {fresh_day: 0.3},
                "vm-stale": {stale_day: 0.9},  # last sample 30 days old
            }
        }
    )
    records = GCPMonitoringProvider(_settings(), query_runner=runner).load_usage()
    assert all(r.resource_id == "vm-fresh" for r in records)
    assert not any(r.resource_id == "vm-stale" for r in records)


def test_stale_metrics_within_age_are_kept() -> None:
    day = datetime.now(UTC).date() - timedelta(days=6)  # within 7-day max age
    runner = _fake_runner({"cpu_utilization": {"vm-1": {day: 0.4}}})
    records = GCPMonitoringProvider(_settings(), query_runner=runner).load_usage()
    assert len(records) == 1


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_provider_failure_wraps_with_context() -> None:
    runner = _fake_runner(error=RuntimeError("503: backend error"))
    provider = GCPMonitoringProvider(_settings(), query_runner=runner)
    with pytest.raises(GCPMonitoringError, match="Cloud Monitoring query failed"):
        provider.load_usage()


def test_provider_failure_is_metric_scoped_but_fatal() -> None:
    """Any metric failing aborts the load: a partial utilization picture (real
    CPU, no memory) must not be silently mistaken for a complete one."""
    day = date(2026, 9, 1)

    def runner(metric, start, end):
        if metric.key == "memory_utilization":
            raise RuntimeError("quota exceeded")
        return {"vm-1": {day: 0.3}}

    provider = GCPMonitoringProvider(_settings(), query_runner=runner)
    with pytest.raises(GCPMonitoringError, match="memory_utilization"):
        provider.load_usage()


def test_missing_monitoring_package_explains_install() -> None:
    """Without google-cloud-monitoring the default runner explains the fix."""
    from costlab.providers import monitoring as monitoring_mod

    settings = _settings()
    runner = monitoring_mod._default_query_runner(settings)
    with pytest.raises(GCPMonitoringError, match="google-cloud-monitoring is not installed"):
        runner(
            monitoring_mod.METRIC_QUERIES["cpu_utilization"],
            date(2026, 9, 1),
            date(2026, 9, 2),
        )


# ---------------------------------------------------------------------------
# Monitoring data strengthens recommendations (cost alone is never enough)
# ---------------------------------------------------------------------------


def _util_row(
    *,
    cpu: float | None,
    requests: float | None = None,
    connections: float | None = None,
    cost: float | None = 30.0,
) -> UtilizationRow:
    from costlab.schemas.cost import PeriodOut
    from costlab.schemas.utilization import MetricStats

    metrics = {}
    if cpu is not None:
        metrics["cpu_utilization"] = MetricStats(
            avg=cpu, min=0.0, max=cpu, p95=cpu, stddev=0.5, sample_count=30
        )
    if requests is not None:
        metrics["request_count"] = MetricStats(
            avg=requests, min=0, max=requests, p95=requests, stddev=1.0, sample_count=30
        )
    if connections is not None:
        metrics["connections"] = MetricStats(
            avg=connections, min=0, max=connections, p95=connections, stddev=0.0, sample_count=30
        )
    metrics["network_in_mb"] = MetricStats(
        avg=5.0, min=0, max=6, p95=5.5, stddev=0.4, sample_count=30
    )
    metrics["network_out_mb"] = MetricStats(
        avg=5.0, min=0, max=6, p95=5.5, stddev=0.4, sample_count=30
    )
    return UtilizationRow(
        resource_id="vm-cost-only",
        resource_name="costly-idle-vm",
        resource_type="vm_instance",
        service_id="compute-engine",
        service_name="Compute Engine",
        project_id="p1",
        project_name="P1",
        environment="development",
        region="us-central1",
        machine_type="e2-standard-4",
        window=PeriodOut(start=date(2026, 8, 1), end=date(2026, 8, 30)),
        metrics=metrics,
        missing_metrics=[m for m in ("connections",) if "connections" not in metrics],
        cost_in_window=cost,
        cost_credits_in_window=0.0,
        cost_net_in_window=cost,
        signals=None,  # type: ignore[arg-type]
    )


def test_idle_recommendation_includes_monitoring_evidence() -> None:
    """The Phase 5 example, now with monitoring corroboration: $30/month AND
    CPU 6% AND >= 14 days of stable samples AND no traffic => idle evidence."""
    rule = IdleComputeRule()
    from costlab.recommendations.engine import EngineContext  # noqa: F401  (structure ref)

    rows = [_util_row(cpu=4.0, requests=2.0)]
    ctx = SimpleNamespace(utilization_rows=rows)
    drafts = rule.evaluate(None, ctx)  # type: ignore[arg-type]
    assert len(drafts) == 1
    draft = drafts[0]
    statements = " ".join(e.statement for e in draft.evidence)
    assert "$30.00" in statements  # cost evidence
    assert "4.0%" in statements  # utilization evidence
    assert "30 days" in statements  # duration evidence
    assert "requests average 2.0/day" in statements  # monitoring corroboration


def test_active_traffic_blocks_idle_recommendation_despite_cost() -> None:
    """A VM serving requests is NOT idle even if its average CPU is low and the
    cost is high — monitoring performance data overrides a cost-only story."""
    rule = IdleComputeRule()
    rows = [_util_row(cpu=6.0, requests=500.0)]
    ctx = SimpleNamespace(utilization_rows=rows)
    assert rule.evaluate(None, ctx) == []  # type: ignore[arg-type]


def test_open_connections_block_idle_recommendation() -> None:
    rule = IdleComputeRule()
    rows = [_util_row(cpu=3.0, requests=1.0, connections=25.0)]
    ctx = SimpleNamespace(utilization_rows=rows)
    assert rule.evaluate(None, ctx) == []  # type: ignore[arg-type]


def test_cost_without_utilization_never_recommends() -> None:
    """No monitoring data at all (cost only) — no recommendation can exist."""
    rule = IdleComputeRule()
    rows = [_util_row(cpu=None, cost=100.0)]
    ctx = SimpleNamespace(utilization_rows=rows)
    assert rule.evaluate(None, ctx) == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Mock provider still works / factory wiring
# ---------------------------------------------------------------------------


def test_mock_monitoring_provider_still_loads(tmp_path) -> None:
    from pathlib import Path

    mock_dir = Path(__file__).resolve().parents[3] / "data" / "mock"
    provider = MockMonitoringProvider(mock_dir)
    assert provider.name == "mock"
    records = provider.load_usage()
    assert len(records) > 0


def test_real_mode_selects_gcp_monitoring_when_configured() -> None:
    from costlab.config import Settings
    from costlab.providers import build_providers

    providers = build_providers(
        Settings(
            demo_mode=False,
            gcp_billing_project="p",
            gcp_billing_dataset="d",
            gcp_billing_table="t",
            gcp_monitoring_project="p",
        )
    )
    assert isinstance(providers.monitoring, GCPMonitoringProvider)
    assert isinstance(providers.monitoring, MonitoringDataProvider)


def test_real_mode_without_monitoring_falls_back_to_empty() -> None:
    from costlab.config import Settings
    from costlab.providers import build_providers

    providers = build_providers(
        Settings(
            demo_mode=False,
            gcp_billing_project="p",
            gcp_billing_dataset="d",
            gcp_billing_table="t",
            gcp_monitoring_project="",
        )
    )
    assert isinstance(providers.monitoring, EmptyMonitoringProvider)
    assert providers.monitoring.load_usage() == []
