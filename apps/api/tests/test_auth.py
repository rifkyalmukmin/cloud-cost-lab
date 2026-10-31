"""API-key authentication on write endpoints."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import delete

from costlab.api.auth import require_principal
from costlab.config import parse_api_keys
from costlab.db.models import AuditLog, Budget

# conftest.py exports the suite's credentials as API_KEYS=<actor>:<key>.
TEST_ACTOR, _, TEST_API_KEY = os.environ["API_KEYS"].partition(":")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Read-only despite using POST (question in, answer out; no state change).
OPEN_POST_ROUTES = {"/api/ai/advisor"}

BUDGET_PAYLOAD = {
    "name": "Auth test budget",
    "scope_type": "all",
    "limit": 50.0,
    "warning_threshold": 70.0,
    "critical_threshold": 90.0,
}


def _requires_auth(dependant: Dependant) -> bool:
    return any(
        dep.call is require_principal or _requires_auth(dep) for dep in dependant.dependencies
    )


def test_every_state_changing_route_requires_api_key(app) -> None:
    """The rule, not an example: a new POST/PUT/PATCH/DELETE route fails here
    unless it depends on require_principal (or is explicitly listed as open)."""
    unprotected = [
        f"{method} {route.path}"
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods - SAFE_METHODS
        if route.path not in OPEN_POST_ROUTES and not _requires_auth(route.dependant)
    ]
    assert unprotected == []


def test_write_without_key_is_401(anon_client: TestClient) -> None:
    response = anon_client.post("/api/recommendations/run")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"
    assert response.json()["error"]["request_id"]


@pytest.mark.parametrize(
    "key", ["wrong-key-0123456789abcdef", TEST_API_KEY[:-1], TEST_API_KEY + "x", ""]
)
def test_write_with_wrong_key_is_401(anon_client: TestClient, key: str) -> None:
    response = anon_client.post("/api/recommendations/run", headers={"X-API-Key": key})
    assert response.status_code == 401


def test_reads_stay_open(anon_client: TestClient) -> None:
    assert anon_client.get("/api/recommendations").status_code == 200
    assert anon_client.get("/api/budget").status_code == 200


def test_rejected_budget_write_creates_nothing(client: TestClient, anon_client: TestClient) -> None:
    before = client.get("/api/budget").json()["summary"]["budget_count"]
    assert anon_client.post("/api/budget", json=BUDGET_PAYLOAD).status_code == 401
    assert client.get("/api/budget").json()["summary"]["budget_count"] == before


def test_audit_actor_is_the_authenticated_identity(client: TestClient, db_session) -> None:
    response = client.post("/api/budget", json=BUDGET_PAYLOAD)
    assert response.status_code == 201
    budget_id = response.json()["id"]
    try:
        logs = client.get("/api/recommendations/audit-logs", params={"entity_id": budget_id}).json()
        assert [(i["action"], i["actor"]) for i in logs["items"]] == [("created", TEST_ACTOR)]
    finally:
        # The session-scoped test database is shared and other budget tests
        # assume they own the budget table: leave no trace.
        db_session.execute(delete(AuditLog).where(AuditLog.entity_id == budget_id))
        db_session.execute(delete(Budget).where(Budget.id == budget_id))
        db_session.commit()


def test_parse_api_keys_maps_key_to_name() -> None:
    parsed = parse_api_keys("alice:" + "a" * 16 + ", bob:" + "b" * 20)
    assert parsed == {"a" * 16: "alice", "b" * 20: "bob"}
    assert parse_api_keys("") == {}


@pytest.mark.parametrize(
    "raw",
    [
        "alice:short",  # key too short
        "no-separator-" + "x" * 16,  # missing name:key shape
        "bad name:" + "a" * 16,  # name outside the allowed charset
        "a:" + "k" * 16 + ",b:" + "k" * 16,  # duplicate key
        "a:" + "k" * 16 + ",a:" + "j" * 16,  # duplicate name
    ],
)
def test_parse_api_keys_rejects_malformed_config(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_api_keys(raw)


# ---------------------------------------------------------------------------
# JWT bearer credentials (Phase 14 hardening: short-lived tokens)
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(
    sub: str = "jwt-user",
    secret: str = "test-jwt-secret-0123456789abcdef",
    *,
    exp_offset: float = 600.0,
    alg: str = "HS256",
    include_exp: bool = True,
    include_sub: bool = True,
) -> str:
    header = {"alg": alg, "typ": "JWT"}
    payload: dict = {}
    if include_exp:
        payload["exp"] = time.time() + exp_offset
    if include_sub:
        payload["sub"] = sub
    header_b64 = _b64url(json.dumps(header).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signature = hmac.new(
        secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
    ).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


def test_bearer_token_grants_write_with_sub_as_actor(client: TestClient, db_session) -> None:
    token = _make_jwt(sub="jwt-user")
    response = client.post(
        "/api/recommendations/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text

    logs = client.get("/api/recommendations/audit-logs", params={"page_size": 5}).json()
    run_rows = [item for item in logs["items"] if item["action"] == "engine_run"]
    assert run_rows, "engine_run audit row missing"
    assert run_rows[0]["actor"] == "jwt-user"  # sub claim -> audit actor


def test_expired_bearer_token_is_401(client: TestClient) -> None:
    token = _make_jwt(exp_offset=-60.0)  # expired an hour... a minute ago
    response = client.post("/api/recommendations/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_bad_signature_bearer_token_is_401(client: TestClient) -> None:
    token = _make_jwt(secret="attacker-secret-not-configured")
    response = client.post("/api/recommendations/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_bearer_token_without_sub_is_401(client: TestClient) -> None:
    token = _make_jwt(include_sub=False)
    response = client.post("/api/recommendations/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_bearer_token_without_exp_is_401(client: TestClient) -> None:
    token = _make_jwt(include_exp=False)
    response = client.post("/api/recommendations/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_alg_none_is_401(client: TestClient) -> None:
    token = _make_jwt(alg="none")
    response = client.post("/api/recommendations/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_malformed_bearer_token_is_401(client: TestClient) -> None:
    for token in ("not-a-jwt", "a.b", "a.b.c"):
        response = client.post(
            "/api/recommendations/run", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401, token


def test_all_failure_modes_share_one_generic_message(client: TestClient) -> None:
    """Do not reveal whether bearer auth is configured, or which part of the
    credential failed."""
    messages = set()
    for token in (
        _make_jwt(exp_offset=-60.0),
        _make_jwt(secret="wrong"),
        _make_jwt(include_sub=False),
        "garbage",
    ):
        response = client.post(
            "/api/recommendations/run", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        # structured error envelope: {"error": {"message": ...}}
        messages.add(response.json()["error"]["message"])
    assert len(messages) == 1
