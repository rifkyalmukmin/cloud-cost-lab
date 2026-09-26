"""Savings verification workflow tests (Phase 13, CLAUDE.md §23).

Covers the full lifecycle OPEN -> APPROVED -> IMPLEMENTED -> VERIFIED plus
the REJECTED branch, the before/after realized-savings calculation against
an independent recomputation from the committed dataset, the honesty guards
(no data -> refuse to verify; double transitions -> 409; negative realized
stored as negative), and the append-only audit trail.

The test DB persists across the session, so these tests reset lifecycle
state first to stay order-independent.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from costlab.db.models import Recommendation

MOCK_DIR_PATH = None  # dataset helpers reuse the module-level pattern


def _load_cost_rows() -> list[dict]:
    import json
    from pathlib import Path

    mock = Path(__file__).resolve().parents[3] / "data" / "mock"
    return json.loads((mock / "cost.json").read_text(encoding="utf-8"))


def _daily_before_after(resource_id: str, implemented_on: date) -> tuple[float, float]:
    """Independent recomputation: daily net-cost averages 30d before/after."""
    rows = _load_cost_rows()
    before_start, before_end = (
        implemented_on - timedelta(days=30),
        implemented_on - timedelta(days=1),
    )
    after_start, after_end = implemented_on, implemented_on + timedelta(days=29)

    def avg(start: date, end: date) -> float:
        vals = [
            Decimal(str(r["net_cost"]))
            for r in rows
            if r["resource_id"] == resource_id
            and start <= date.fromisoformat(r["usage_date"]) <= end
        ]
        return float(sum(vals) / len(vals))

    return avg(before_start, before_end), avg(after_start, after_end)


def _reset_lifecycle(db_session) -> None:
    db_session.execute(
        update(Recommendation).values(
            status="OPEN",
            implemented_at=None,
            verified_at=None,
            actual_cost_after=None,
            realized_savings=None,
        )
    )
    db_session.commit()


def _idle_id(client: TestClient) -> str:
    body = client.get("/api/recommendations", params={"rule_id": "idle_compute"}).json()
    return body["items"][0]["id"]


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def test_full_lifecycle_approve_implement_verify(client: TestClient, db_session) -> None:
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    rec_id = _idle_id(client)

    approved = client.post(f"/api/recommendations/{rec_id}/approve")
    assert approved.json()["status"] == "APPROVED"

    # backfill the implementation date INTO the data span so after-data exists
    implemented_on = date(2026, 8, 1)
    implemented = client.post(
        f"/api/recommendations/{rec_id}/implement",
        json={"implemented_at": f"{implemented_on.isoformat()}T00:00:00Z"},
    )
    assert implemented.json()["status"] == "IMPLEMENTED"

    verified = client.post(f"/api/recommendations/{rec_id}/verify")
    assert verified.status_code == 200
    body = verified.json()
    assert body["status"] == "VERIFIED"
    assert body["source"] == "data"
    assert body["before_days"] == 30 and body["after_days"] == 30

    # realized savings equals the independent before/after recomputation
    before_daily, after_daily = _daily_before_after("vm-report-dev-1", implemented_on)
    expected = round((before_daily - after_daily) * 30.0, 4)
    assert body["realized_savings"] == pytest.approx(expected, abs=0.01)
    assert body["after_daily_avg"] == pytest.approx(after_daily, abs=0.01)

    # the detail endpoint exposes the realized number, and actual_cost_after
    detail = client.get(f"/api/recommendations/{rec_id}").json()
    assert detail["realized_savings"] == pytest.approx(expected, abs=0.01)
    assert detail["actual_cost_after"] == pytest.approx(after_daily * 30.0, abs=0.01)
    assert detail["verified_at"] is not None and detail["implemented_at"] is not None


def test_rejection_branch(client: TestClient, db_session) -> None:
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    body = client.get("/api/recommendations", params={"rule_id": "oversized_compute"}).json()
    rec_id = body["items"][0]["id"]

    rejected = client.post(f"/api/recommendations/{rec_id}/reject")
    assert rejected.json()["status"] == "REJECTED"
    # rejected recommendations cannot move anywhere else
    assert client.post(f"/api/recommendations/{rec_id}/approve").status_code == 409
    assert client.post(f"/api/recommendations/{rec_id}/implement").status_code == 409
    assert client.post(f"/api/recommendations/{rec_id}/verify").status_code == 409


# ---------------------------------------------------------------------------
# Honesty guards
# ---------------------------------------------------------------------------


def test_transitions_require_the_right_source_status(client: TestClient, db_session) -> None:
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    rec_id = _idle_id(client)

    # OPEN -> IMPLEMENTED directly is forbidden
    assert client.post(f"/api/recommendations/{rec_id}/implement").status_code == 409
    # OPEN -> VERIFIED directly is forbidden
    assert client.post(f"/api/recommendations/{rec_id}/verify").status_code == 409
    # approve once, then a second approve is invalid
    assert client.post(f"/api/recommendations/{rec_id}/approve").status_code == 200
    assert client.post(f"/api/recommendations/{rec_id}/approve").status_code == 409


def test_verify_without_after_data_refuses(client: TestClient, db_session) -> None:
    """Implemented 'now' means no post-change cost data exists in the
    date-anchored dataset: verification must refuse rather than claim
    realized savings (409), leaving the number honest."""
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    rec_id = _idle_id(client)
    client.post(f"/api/recommendations/{rec_id}/approve")
    client.post(f"/api/recommendations/{rec_id}/implement")  # implemented_at = now

    response = client.post(f"/api/recommendations/{rec_id}/verify")
    assert response.status_code == 409
    assert "Cannot verify" in response.json()["error"]["message"]
    # and the recommendation is still IMPLEMENTED with no realized number
    detail = client.get(f"/api/recommendations/{rec_id}").json()
    assert detail["status"] == "IMPLEMENTED"
    assert detail["realized_savings"] is None


def test_reported_actual_is_accepted_but_labelled(client: TestClient, db_session) -> None:
    """An externally measured actual cost after the change may drive
    verification (source='reported'); simulated estimates still never pass
    through here."""
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    rec_id = _idle_id(client)
    client.post(f"/api/recommendations/{rec_id}/approve")
    client.post(f"/api/recommendations/{rec_id}/implement")

    response = client.post(f"/api/recommendations/{rec_id}/verify", json={"actual_cost_after": 1.0})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "reported"
    assert body["status"] == "VERIFIED"
    assert body["realized_savings"] is not None


def test_negative_realized_is_stored_honestly(client: TestClient, db_session) -> None:
    """If post-change cost went UP, realized savings is negative — stored as
    measured, never clamped to zero (CLAUDE.md §4: no rosy claims)."""
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    body = client.get("/api/recommendations", params={"rule_id": "oversized_compute"}).json()
    rec_id = body["items"][0]["id"]

    client.post(f"/api/recommendations/{rec_id}/approve")
    implemented_on = date(2026, 8, 1)
    client.post(
        f"/api/recommendations/{rec_id}/implement",
        json={"implemented_at": f"{implemented_on.isoformat()}T00:00:00Z"},
    )
    # reported actual AFTER is higher than the before run-rate: costs rose
    verified = client.post(
        f"/api/recommendations/{rec_id}/verify", json={"actual_cost_after": 999.0}
    )
    assert verified.status_code == 200
    assert verified.json()["realized_savings"] < 0


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


def test_audit_log_records_every_transition(client: TestClient, db_session) -> None:
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    rec_id = _idle_id(client)

    client.post(f"/api/recommendations/{rec_id}/approve")
    client.post(
        f"/api/recommendations/{rec_id}/implement",
        json={"implemented_at": "2026-08-01T00:00:00Z"},
    )
    client.post(f"/api/recommendations/{rec_id}/verify")

    logs = client.get(
        "/api/recommendations/audit-logs", params={"entity_id": rec_id, "page_size": 50}
    ).json()
    actions = [item["action"] for item in logs["items"]]
    # the trail is append-only across the session: this test's three newest
    # entries must sit on top, newest first
    assert actions[:3] == ["verified", "implemented", "approved"]
    for item in logs["items"]:
        assert item["actor"] == "local-user"
        assert item["entity_type"] == "recommendation"
        assert item["details"].get("from")
    # append-only spot check: ids strictly decrease with age
    ids = [item["timestamp"] for item in logs["items"]]
    assert ids == sorted(ids, reverse=True)


# ---------------------------------------------------------------------------
# Savings summary endpoint
# ---------------------------------------------------------------------------


def test_savings_summary_distinguishes_potential_from_realized(
    client: TestClient, db_session
) -> None:
    _reset_lifecycle(db_session)
    client.post("/api/recommendations/run")
    rec_id = _idle_id(client)

    # potential exists immediately (OPEN)
    before = client.get("/api/recommendations/savings").json()
    assert before["potential_savings"] > 0
    assert before["realized_savings"] == 0.0  # nothing verified yet

    client.post(f"/api/recommendations/{rec_id}/approve")
    client.post(
        f"/api/recommendations/{rec_id}/implement",
        json={"implemented_at": "2026-08-01T00:00:00Z"},
    )
    client.post(f"/api/recommendations/{rec_id}/verify")

    after = client.get("/api/recommendations/savings").json()
    # realized is now measured from actual before/after data
    assert after["realized_savings"] != 0.0
    assert after["verified"]["count"] >= 1
    # potential remains the estimate; realized is the measured number —
    # they are different quantities and both are shown
    assert after["potential_savings"] > 0
    detail = client.get(f"/api/recommendations/{rec_id}").json()
    assert after["realized_savings"] == pytest.approx(detail["realized_savings"], abs=0.01)
