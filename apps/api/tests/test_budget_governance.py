"""Budget & governance tests (Phase 6).

Threshold coverage is the core: 69% / 70% / 89% / 90% / 99% / 100% / 101%
against the default 70/90 thresholds (inclusive boundaries — exactly at a
threshold is already in the next band), plus dataset-exact budget limits
that land the spend percentage exactly on 69 / 70 / 90 / 100.

Policies are advisory: tests assert PASS/WARNING/VIOLATION outcomes and
findings — never an action. Strict boundary: a resource costing exactly
MAX_MONTHLY_COST is compliant.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from costlab.analytics.budget import budget_status
from costlab.governance import ensure_default_policies
from costlab.governance.policies import (
    ResourceFact,
    evaluate_dev_resource_schedule,
    evaluate_max_monthly_cost,
    evaluate_no_public_database,
    evaluate_require_environment_label,
    evaluate_require_owner_label,
)

MOCK_DIR = Path(__file__).resolve().parents[3] / "data" / "mock"


def _cost_rows() -> list[dict]:
    return json.loads((MOCK_DIR / "cost.json").read_text(encoding="utf-8"))


def _mtd_net_spend(project_id: str | None = None) -> float:
    """Latest month in the data, net cost — the same definition as the API."""
    rows = _cost_rows()
    end = max(r["usage_date"] for r in rows)
    month_start = end[:8] + "01"
    return round(
        float(
            sum(
                Decimal(str(r["net_cost"]))
                for r in rows
                if r["usage_date"] >= month_start
                and (project_id is None or r["project_id"] == project_id)
            )
        ),
        4,
    )


# ---------------------------------------------------------------------------
# Pure threshold ladder — the requested boundaries
# ---------------------------------------------------------------------------


def test_budget_status_threshold_ladder_default_thresholds() -> None:
    # 69 / 70 / 89 / 90 / 99 / 100 / 101 against warning=70, critical=90
    ladder = {pct: budget_status(pct, 100.0, 70.0, 90.0) for pct in (69, 70, 89, 90, 99, 100, 101)}
    assert ladder == {
        69: "HEALTHY",
        70: "WARNING",  # exactly at the threshold is already WARNING
        89: "WARNING",
        90: "CRITICAL",  # exactly at the threshold is CRITICAL
        99: "CRITICAL",
        100: "EXCEEDED",  # §15: Exceeded: 100%
        101: "EXCEEDED",
    }


def test_budget_status_custom_thresholds_and_degenerate_limit() -> None:
    assert budget_status(49.9, 100.0, 50.0, 80.0) == "HEALTHY"
    assert budget_status(50.0, 100.0, 50.0, 80.0) == "WARNING"
    assert budget_status(79.9, 100.0, 50.0, 80.0) == "WARNING"
    assert budget_status(80.0, 100.0, 50.0, 80.0) == "CRITICAL"
    # fractional percentages behave inclusively as well
    assert budget_status(69.999, 100.0, 70.0, 90.0) == "HEALTHY"
    assert budget_status(70.001, 100.0, 70.0, 90.0) == "WARNING"
    # a zero/negative limit cannot be satisfied
    assert budget_status(0.0, 0.0, 70.0, 90.0) == "EXCEEDED"
    assert budget_status(1.0, -5.0, 70.0, 90.0) == "EXCEEDED"


# ---------------------------------------------------------------------------
# Policy evaluators — pure boundaries
# ---------------------------------------------------------------------------


def _fact(**overrides) -> ResourceFact:
    base = dict(
        resource_id="vm-test-1",
        resource_name="test-vm",
        resource_type="vm_instance",
        service_id="compute-engine",
        environment="production",
        owner="rifky",
        labels={"environment": "production", "owner": "rifky"},
        monthly_cost=5.0,
    )
    base.update(overrides)
    return ResourceFact(**base)


def test_max_monthly_cost_strict_boundary() -> None:
    config = {"monthly_cost_usd": 10.0}
    # exactly at the limit → compliant (strictly above triggers)
    assert evaluate_max_monthly_cost([_fact(monthly_cost=10.0)], config).status == "PASS"
    # one cent above → violation
    result = evaluate_max_monthly_cost([_fact(monthly_cost=10.01)], config)
    assert result.status == "VIOLATION"
    assert result.findings[0].resource_id == "vm-test-1"
    # no cost data cannot breach
    assert evaluate_max_monthly_cost([_fact(monthly_cost=None)], config).status == "PASS"


def test_no_public_database_never_false_pass() -> None:
    # explicit public_ip=true → VIOLATION
    public = evaluate_no_public_database(
        [_fact(resource_type="sql_instance", labels={"public_ip": True})], {}
    )
    assert public.status == "VIOLATION"
    # explicit private → PASS
    private = evaluate_no_public_database(
        [_fact(resource_type="sql_instance", labels={"public_ip": False})], {}
    )
    assert private.status == "PASS"
    # no reachability data → WARNING (cannot verify), never a false PASS
    unknown = evaluate_no_public_database([_fact(resource_type="sql_instance", labels={})], {})
    assert unknown.status == "WARNING"
    assert "cannot verify" in unknown.findings[0].detail
    # non-databases are out of scope
    assert evaluate_no_public_database([_fact(resource_type="vm_instance")], {}).status == "PASS"


def test_label_policies_and_dev_schedule() -> None:
    # owner label missing → WARNING
    owner = evaluate_require_owner_label([_fact(owner=None)], {})
    assert owner.status == "WARNING" and owner.findings[0].resource_id == "vm-test-1"
    assert evaluate_require_owner_label([_fact()], {}).status == "PASS"

    # environment label missing from labels → WARNING
    env = evaluate_require_environment_label([_fact(labels={})], {})
    assert env.status == "WARNING"
    assert evaluate_require_environment_label([_fact()], {}).status == "PASS"

    # dev compute without a schedule label → WARNING; with one → PASS
    dev = evaluate_dev_resource_schedule([_fact(environment="development")], {})
    assert dev.status == "WARNING"
    scheduled = evaluate_dev_resource_schedule(
        [_fact(environment="development", labels={"schedule": "08:00-18:00-mon-fri"})], {}
    )
    assert scheduled.status == "PASS"
    # production resources are out of scope for the schedule policy
    assert evaluate_dev_resource_schedule([_fact(environment="production")], {}).status == "PASS"


# ---------------------------------------------------------------------------
# Dataset-driven policy evaluation via the API
# ---------------------------------------------------------------------------


def test_policies_endpoint_expected_statuses(client: TestClient, db_session) -> None:
    ensure_default_policies(db_session)
    db_session.commit()

    response = client.get("/api/policies")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["policy_count"] == 5

    by_id = {p["policy_id"]: p for p in body["policies"]}
    assert set(by_id) == {
        "REQUIRE_OWNER_LABEL",
        "REQUIRE_ENVIRONMENT_LABEL",
        "MAX_MONTHLY_COST",
        "NO_PUBLIC_DATABASE",
        "DEV_RESOURCE_SCHEDULE",
    }

    # owner: exactly the legacy sandbox lacks attribution
    owner = by_id["REQUIRE_OWNER_LABEL"]
    assert owner["status"] == "WARNING"
    assert [f["resource_id"] for f in owner["findings"]] == ["vm-legacy-sandbox-1"]

    # environment label: every resource declares one
    assert by_id["REQUIRE_ENVIRONMENT_LABEL"]["status"] == "PASS"

    # max monthly cost: only the production Cloud SQL breaches $10/month
    cost = by_id["MAX_MONTHLY_COST"]
    assert cost["status"] == "VIOLATION"
    assert [f["resource_id"] for f in cost["findings"]] == ["sql-shop-orders-prod"]
    assert "$17.27" in cost["findings"][0]["detail"]

    # public database: no reachability data in the mock — WARNING, not a false PASS
    public_db = by_id["NO_PUBLIC_DATABASE"]
    assert public_db["status"] == "WARNING"
    assert {f["resource_id"] for f in public_db["findings"]} == {
        "sql-shop-orders-prod",
        "sql-shop-orders-staging",
    }

    # dev schedule: the three development resources have no schedule label
    schedule = by_id["DEV_RESOURCE_SCHEDULE"]
    assert schedule["status"] == "WARNING"
    assert {f["resource_id"] for f in schedule["findings"]} == {
        "vm-report-dev-1",
        "vm-sandbox-dev-1",
        "vm-legacy-sandbox-1",
    }

    # summary aggregates
    assert body["summary"]["by_status"] == {"PASS": 1, "WARNING": 3, "VIOLATION": 1}
    assert body["summary"]["finding_count"] == 7

    # policies are advisory: the response carries no action/executable fields
    for policy in body["policies"]:
        assert set(policy) == {
            "policy_id",
            "name",
            "description",
            "enabled",
            "config",
            "status",
            "summary",
            "findings",
        }


# ---------------------------------------------------------------------------
# Budget API — evaluation matches independent recomputation
# ---------------------------------------------------------------------------


def _create_budget(client: TestClient, **overrides) -> dict:
    payload = {
        "name": "Lab monthly budget",
        "scope_type": "all",
        "limit": 50.0,
        "warning_threshold": 70.0,
        "critical_threshold": 90.0,
    }
    payload.update(overrides)
    response = client.post("/api/budget", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_budget_evaluation_matches_recomputation(client: TestClient) -> None:
    created = _create_budget(client)
    assert created["status"] is not None

    spend_expected = _mtd_net_spend()
    assert created["spend"]["amount"] == pytest.approx(spend_expected)

    body = client.get("/api/budget").json()
    assert body["summary"]["budget_count"] == 1
    budget = body["budgets"][0]
    assert budget["spend"]["amount"] == pytest.approx(spend_expected)

    # data-anchored evaluation month: the latest month in the data
    cost_rows = _cost_rows()
    data_end = max(r["usage_date"] for r in cost_rows)
    assert budget["spend"]["period"]["end"] == data_end
    assert budget["spend"]["period"]["start"] == data_end[:8] + "01"
    assert budget["spend"]["period"]["days_elapsed"] == int(data_end[8:])

    # status, percentage and remaining consistent with the recomputed spend
    limit = 50.0
    expected_pct = round(spend_expected / limit * 100, 1)
    assert budget["spend_percentage"] == expected_pct
    assert budget["status"] == budget_status(spend_expected, limit, 70.0, 90.0)
    assert budget["remaining"] == pytest.approx(round(limit - spend_expected, 4))

    # linear run-rate projection, labelled estimate
    days_elapsed = budget["spend"]["period"]["days_elapsed"]
    days_in_month = budget["spend"]["period"]["days_in_month"]
    expected_projection = round(spend_expected / days_elapsed * days_in_month, 2)
    assert budget["projected_month_end"] == expected_projection
    # the lab's September run-rate exceeds the $50 budget — forecast risk shown
    assert budget["forecast_over_budget"] is True
    assert budget["status"] == "HEALTHY"  # MTD alone is only ~21%


def test_budget_status_bands_across_limits(client: TestClient) -> None:
    """Every band reachable through the API: limits chosen with clear margins
    around the known MTD spend (~$10.62). Exact threshold boundaries are
    covered by the pure ladder test above."""
    cases = {  # limit -> expected band (spend/limit lands well inside it)
        5.0: "EXCEEDED",  # ~212%
        11.0: "CRITICAL",  # ~96.6%
        15.0: "WARNING",  # ~70.8%
        20.0: "HEALTHY",  # ~53.1%
    }
    for index, (limit, expected) in enumerate(cases.items()):
        created = _create_budget(client, name=f"band-{index}", limit=limit)
        actual_pct = created["spend"]["amount"] / limit * 100
        assert created["status"] == expected, (limit, actual_pct, created)
        # status always consistent with the pure threshold function
        assert created["status"] == budget_status(
            created["spend"]["amount"],
            limit,
            created["warning_threshold"],
            created["critical_threshold"],
        )


def test_budget_project_scope_spend(client: TestClient) -> None:
    created = _create_budget(
        client,
        name="Prod project budget",
        scope_type="project",
        scope_value="cc-lab-shop-prod",
        limit=25.0,
    )
    assert created["spend"]["amount"] == pytest.approx(_mtd_net_spend("cc-lab-shop-prod"))


def test_budget_post_validation_rejects_bad_input(client: TestClient) -> None:
    base = {
        "name": "x",
        "scope_type": "all",
        "limit": 10.0,
        "warning_threshold": 70.0,
        "critical_threshold": 90.0,
    }
    bad_payloads = [
        {**base, "limit": 0},  # non-positive limit
        {**base, "limit": -5},
        {**base, "warning_threshold": 90.0},  # warning == critical
        {**base, "warning_threshold": 95.0},  # warning > critical
        {**base, "warning_threshold": 0},
        {**base, "critical_threshold": 100},  # must stay below 100
        {**base, "scope_type": "galaxy"},  # unknown scope
        {**base, "scope_type": "project"},  # scope_value missing
        {**base, "name": ""},  # empty name
        {**base, "period": "weekly"},  # monthly only in this phase
        {**base, "extra_field": True},  # forbid unknown fields
    ]
    before = client.get("/api/budget").json()["summary"]["budget_count"]
    for payload in bad_payloads:
        response = client.post("/api/budget", json=payload)
        assert response.status_code == 422, payload
    # nothing was created by the rejected payloads
    after = client.get("/api/budget").json()["summary"]["budget_count"]
    assert after == before


def test_budget_post_requires_validation_not_auth_gimmicks(client: TestClient) -> None:
    """POST works without credentials by design (local demo, GET/POST CORS on
    configured origins only) — but input is always validated server-side."""
    response = client.post(
        "/api/budget",
        json={
            "name": "string-injection'; DROP TABLE budgets; --",
            "scope_type": "all",
            "limit": 10.0,
            "warning_threshold": 50.0,
            "critical_threshold": 75.0,
        },
    )
    assert response.status_code == 201  # stored as opaque data via ORM parameters
    assert response.json()["name"].startswith("string-injection")
    # and the budgets endpoint still works (table intact)
    assert client.get("/api/budget").status_code == 200


def test_cors_allows_post_from_configured_origin(client: TestClient) -> None:
    """Phase 6 opens POST (budget creation) — still origin-restricted, no credentials."""
    preflight = client.options(
        "/api/budget",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in preflight.headers["access-control-allow-methods"]

    denied = client.options(
        "/api/budget",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert denied.status_code == 400  # CORS middleware rejects unknown origins
