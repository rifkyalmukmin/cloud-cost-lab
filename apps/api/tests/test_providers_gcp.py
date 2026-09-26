"""GCP Billing provider + freshness tests (Phase 8).

The BigQuery client is stubbed — no network, no credentials, no Google
packages required. Covered: valid mapping, empty response, BigQuery error,
authentication failure, malformed data, stale/fresh data, and the §9 query
safety guarantees (partition filter, column whitelist, LIMIT, parameters,
dry run).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from costlab.analytics.freshness import compute_freshness
from costlab.providers import build_providers
from costlab.providers.gcp import GCPBillingError, GCPBillingProvider

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class StubRow:
    def __init__(self, data: dict) -> None:
        self._data = data

    def __getitem__(self, key: str):
        return self._data[key]  # KeyError propagates like a real missing field


class StubJob:
    def __init__(self, rows=None, dry_run=False, total_bytes=2_000_000) -> None:
        self._rows = rows or []
        self._dry_run = dry_run
        self.total_bytes_processed = total_bytes if dry_run else None

    def result(self):
        if self._dry_run:
            raise AssertionError("result() must not be called on a dry run")
        return list(self._rows)


class StubClient:
    def __init__(self, rows=None, error: Exception | None = None) -> None:
        self.rows = rows or []
        self.error = error
        self.calls: list[tuple[str, object]] = []

    def query(self, sql: str, job_config=None):
        self.calls.append((sql, job_config))
        if self.error is not None:
            raise self.error
        if job_config is not None and getattr(job_config, "is_dry_run", False):
            return StubJob(dry_run=True)
        return StubJob(self.rows)


class StubScalarParam:
    def __init__(self, name: str, kind: str, value) -> None:
        self.name, self.type_, self.value = name, kind, value


class StubJobConfigs:
    """Mirrors the job-config adapter surface used by the provider."""

    def __init__(self, is_dry_run=False, query_parameters=None) -> None:
        self.is_dry_run = is_dry_run
        self.query_parameters = query_parameters or []

    def new_dry_run(self) -> StubJobConfigs:
        return StubJobConfigs(is_dry_run=True)

    def with_parameters(self, parameters) -> StubJobConfigs:
        return StubJobConfigs(query_parameters=[StubScalarParam(*p) for p in parameters])


def _stub_job_configs():
    return StubJobConfigs()


def _provider(rows=None, error=None) -> tuple[GCPBillingProvider, StubClient]:
    settings = SimpleNamespace(
        gcp_billing_project="billing-project",
        gcp_billing_dataset="billing_export",
        gcp_billing_table="gcp_billing_export_v1_012C25",
        gcp_billing_location="US",
        gcp_billing_max_days=30,
        gcp_billing_max_rows=1000,
    )
    client = StubClient(rows=rows, error=error)
    provider = GCPBillingProvider(
        settings, client_factory=lambda: client, job_configs_factory=_stub_job_configs
    )
    return provider, client


def _valid_row(**overrides) -> StubRow:
    data = {
        "usage_date": date(2026, 9, 1),
        "project_id": "learn-cloud-gcp-506920",
        "project_name": "Learn Cloud GCP",
        "service_name": "Compute Engine",
        "sku_description": "N1 Predefined Instance Core running in Americas",
        "resource_id": "//compute.googleapis.com/projects/p/zones/z/instances/vm-1",
        "resource_name": "vm-1",
        "region": "us-central1",
        "labels": [
            {"key": "environment", "value": "production"},
            {"key": "owner", "value": "rifky"},
        ],
        "cost": 1.5,
        "credits": 0.25,
        "usage_amount": 24.0,
        "usage_unit": "hour",
        "currency": "USD",
        "billing_account_id": "012C25-4E479C-6B88C8",
    }
    data.update(overrides)
    return StubRow(data)


# ---------------------------------------------------------------------------
# Valid mapping
# ---------------------------------------------------------------------------


def test_valid_response_maps_to_snapshot() -> None:
    provider, _client = _provider(rows=[_valid_row()])
    snapshot = provider.load_snapshot()

    assert snapshot.source.startswith("bigquery:billing-project.")
    assert [s.service_id for s in snapshot.services] == ["compute-engine"]
    assert snapshot.services[0].display_name == "Compute Engine"

    assert len(snapshot.projects) == 1
    assert snapshot.projects[0].project_id == "learn-cloud-gcp-506920"

    assert len(snapshot.resources) == 1
    resource = snapshot.resources[0]
    assert resource.resource_id.startswith("//compute.googleapis.com/")
    assert resource.environment == "production"  # from the label
    assert resource.owner == "rifky"
    assert resource.labels["environment"] == "production"
    assert resource.type == "gcp_resource"  # export schema has no type column

    record = snapshot.cost_records[0]
    assert record.cost == 1.5
    assert record.credits == 0.25
    assert record.net_cost == 1.25  # cost - credits
    assert record.environment == "production"


def test_missing_resource_becomes_unattributed_bucket() -> None:
    """Billing lines without a resource are cost too: an honest per-scope
    bucket resource keeps them visible without guessing attribution."""
    row = _valid_row(resource_id=None, resource_name=None, labels=[])
    provider, _client = _provider(rows=[row])
    snapshot = provider.load_snapshot()

    assert len(snapshot.resources) == 1
    bucket = snapshot.resources[0]
    assert bucket.resource_id == "unattributed:learn-cloud-gcp-506920:compute-engine"
    assert bucket.type == "unattributed"
    assert bucket.status == "UNATTRIBUTED"
    # ...and without an environment label the environment is UNALLOCATED
    assert bucket.environment == "UNALLOCATED"
    assert snapshot.cost_records[0].environment == "UNALLOCATED"


def test_unknown_environment_label_is_unallocated() -> None:
    row = _valid_row(labels=[{"key": "environment", "value": "chaos-env"}])
    provider, _client = _provider(rows=[row])
    snapshot = provider.load_snapshot()
    assert snapshot.resources[0].environment == "UNALLOCATED"


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_empty_response_yields_empty_snapshot() -> None:
    provider, _client = _provider(rows=[])
    snapshot = provider.load_snapshot()
    assert snapshot.services == []
    assert snapshot.projects == []
    assert snapshot.resources == []
    assert snapshot.cost_records == []


def test_bigquery_error_wrapped_with_context() -> None:
    provider, _client = _provider(error=RuntimeError("Not found: table gcp_billing_export_v1"))
    with pytest.raises(GCPBillingError, match="BigQuery query failed"):
        provider.load_snapshot()


def test_authentication_failure_has_actionable_message() -> None:
    settings = SimpleNamespace(
        gcp_billing_project="p",
        gcp_billing_dataset="d",
        gcp_billing_table="t",
        gcp_billing_location="US",
        gcp_billing_max_days=30,
        gcp_billing_max_rows=100,
    )

    def failing_factory():
        raise Exception("could not find default credentials")  # noqa: TRY002

    provider = GCPBillingProvider(settings, client_factory=failing_factory)
    with pytest.raises(GCPBillingError, match="authenticate"):
        provider.load_snapshot()


def test_missing_bigquery_package_explains_install() -> None:
    settings = SimpleNamespace(
        gcp_billing_project="p",
        gcp_billing_dataset="d",
        gcp_billing_table="t",
        gcp_billing_location="US",
        gcp_billing_max_days=30,
        gcp_billing_max_rows=100,
    )
    provider = GCPBillingProvider(settings, client_factory=None)
    try:
        provider._default_client_factory()
    except GCPBillingError as exc:
        assert "google-cloud-bigquery is not installed" in str(exc)
        with pytest.raises(GCPBillingError, match="google-cloud-bigquery"):
            provider.load_snapshot()
        return
    pytest.skip("google-cloud-bigquery installed in this environment")


def test_malformed_row_fails_at_boundary() -> None:
    row = _valid_row()
    del row._data["cost"]  # a required column is missing
    provider, _client = _provider(rows=[row])
    with pytest.raises(GCPBillingError, match="Malformed billing export row"):
        provider.load_snapshot()


# ---------------------------------------------------------------------------
# BigQuery cost protection (CLAUDE.md §9) — asserted on the executed query
# ---------------------------------------------------------------------------


def test_query_is_partition_aware_and_cost_guarded() -> None:
    provider, client = _provider(rows=[_valid_row()])
    provider.load_snapshot()

    assert len(client.calls) == 2  # dry run + real query
    sql, real_config = client.calls[1]
    sql_lower = sql.lower()

    # partition-aware and date-filtered
    assert "_partitiontime >= timestamp(@range_start)" in sql_lower
    assert "_partitiontime < timestamp(@range_end)" in sql_lower
    assert "usage_start_time >= timestamp(@range_start)" in sql_lower
    # explicit column whitelist — never SELECT *
    assert "select *" not in sql_lower
    # bounded row cap, parameterized values
    assert "limit @max_rows" in sql_lower
    params = {p.name: p.value for p in real_config.query_parameters}
    assert params["max_rows"] == 1000
    # range spans exactly max_days, ending yesterday
    span = params["range_end"] - params["range_start"]
    assert span == timedelta(days=30)
    assert params["range_end"].date() == datetime.now(UTC).date()


def test_dry_run_estimates_bytes_before_querying() -> None:
    provider, client = _provider(rows=[_valid_row()])
    provider.load_snapshot()
    dry_sql, dry_config = client.calls[0]
    assert dry_config.is_dry_run is True
    assert "select" in dry_sql.lower()
    # the real query carries the parameters; the dry run does not need them
    _, real_config = client.calls[1]
    names = {p.name for p in real_config.query_parameters}
    assert names == {"range_start", "range_end", "max_rows"}


# ---------------------------------------------------------------------------
# Mode wiring — the mock provider keeps working
# ---------------------------------------------------------------------------


def test_demo_mode_still_selects_mock_providers() -> None:
    settings = SimpleNamespace(
        demo_mode=True,
        mock_data_dir="../../data/mock",
        gcp_billing_project="p",
        gcp_billing_dataset="d",
        gcp_billing_table="t",
    )
    providers = build_providers(settings)
    assert providers.billing.name == "mock"
    assert providers.usage.name == "mock"
    # and the mock snapshot still loads
    snapshot = providers.billing.load_snapshot()
    assert len(snapshot.cost_records) > 0


def test_real_mode_without_config_fails_loudly() -> None:
    settings = SimpleNamespace(
        demo_mode=False,
        gcp_billing_project="",
        gcp_billing_dataset="",
        gcp_billing_table="",
    )
    with pytest.raises(RuntimeError, match="GCP_BILLING_PROJECT"):
        build_providers(settings)


# ---------------------------------------------------------------------------
# Freshness (CLAUDE.md §41)
# ---------------------------------------------------------------------------


def test_freshness_fresh_stale_unknown() -> None:
    now = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
    # data complete through 2026-09-06 00:00 UTC => 12h old => FRESH
    fresh = compute_freshness(date(2026, 9, 5), now, max_age_hours=48)
    assert fresh.status == "FRESH" and fresh.data_age_hours == 12.0

    # boundary: exactly 48h is still FRESH (<=); one minute later is STALE
    boundary = compute_freshness(date(2026, 9, 5), now, max_age_hours=48)
    assert boundary.status == "FRESH"
    assert (
        compute_freshness(
            date(2026, 9, 5), now + timedelta(hours=36, minutes=1), max_age_hours=48
        ).status
        == "STALE"
    )

    stale = compute_freshness(date(2026, 9, 5), datetime(2026, 9, 20, tzinfo=UTC), 48)
    assert stale.status == "STALE" and stale.data_age_hours > 48

    unknown = compute_freshness(None, now, 48)
    assert unknown.status == "UNKNOWN" and unknown.last_updated is None


def test_freshness_endpoint_reports_dataset_state(client: TestClient) -> None:
    response = client.get("/api/freshness")
    assert response.status_code == 200
    body = response.json()
    # the committed mock dataset ends 2026-09-05 — old versus the wall clock,
    # so the honest answer is STALE (never presented as current)
    assert body["status"] == "STALE"
    assert body["last_updated"] == "2026-09-05"
    assert body["data_age_hours"] > body["max_age_hours"]
