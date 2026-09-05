"""API tests: pagination, filtering, validation, error handling, request ids."""

from __future__ import annotations

import math

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "cloud-cost-lab-api"
    assert body["demo_mode"] is True


def test_ready(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_openapi_schema_available(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/health",
        "/ready",
        "/api/cost",
        "/api/cost/trend",
        "/api/cost/by-service",
        "/api/cost/by-project",
        "/api/cost/by-environment",
    ):
        assert path in paths


def test_cost_endpoint_pagination(client: TestClient) -> None:
    response = client.get("/api/cost", params={"page": 1, "page_size": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == 1164
    assert body["pagination"]["total_pages"] == math.ceil(1164 / 5)
    assert len(body["items"]) == 5
    assert body["summary"]["cost"] > 0

    page2 = client.get("/api/cost", params={"page": 2, "page_size": 5}).json()
    # rows are ordered by (date desc, id desc); many rows share a date, so
    # compare row identity, not just the date
    identity = lambda items: [(i["usage_date"], i["resource_id"]) for i in items]  # noqa: E731
    assert identity(body["items"]) != identity(page2["items"])


def test_cost_endpoint_filters(client: TestClient) -> None:
    response = client.get(
        "/api/cost",
        params={
            "service": "compute-engine",
            "environment": "production",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == 93  # 3 production VMs x 31 days
    for item in body["items"]:
        assert item["service"] == "compute-engine"
        assert item["environment"] == "production"
        assert "2026-08-01" <= item["usage_date"] <= "2026-08-31"


def test_cost_endpoint_unknown_filter_returns_empty(client: TestClient) -> None:
    response = client.get("/api/cost", params={"project_id": "no-such-project"})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["pagination"]["total_items"] == 0
    assert body["summary"]["cost"] == 0.0


def test_trend_granularities(client: TestClient) -> None:
    month = client.get("/api/cost/trend", params={"granularity": "month"}).json()
    assert len(month["points"]) == 4
    week = client.get("/api/cost/trend", params={"granularity": "week"}).json()
    assert len(week["points"]) == 14
    day = client.get("/api/cost/trend", params={"granularity": "day"}).json()
    assert len(day["points"]) == 97
    # all granularities must sum to the same total (within rounding)
    totals = [round(sum(p["cost"] for p in b["points"]), 2) for b in (day, week, month)]
    assert max(totals) - min(totals) < 0.01


def test_by_service_shares_sum_to_100(client: TestClient) -> None:
    body = client.get("/api/cost/by-service").json()
    assert len(body["rows"]) == 4
    # shares are rounded to 2dp per row, so the sum can drift slightly from 100
    assert abs(sum(row["share_pct"] for row in body["rows"]) - 100) <= 0.05
    # rows sorted by cost desc
    costs = [row["cost"] for row in body["rows"]]
    assert costs == sorted(costs, reverse=True)


def test_by_project_includes_unallocated_project(client: TestClient) -> None:
    body = client.get("/api/cost/by-project").json()
    projects = {row["project_id"]: row for row in body["rows"]}
    assert "cc-lab-legacy-sandbox" in projects
    assert projects["cc-lab-legacy-sandbox"]["cost"] > 0
    assert abs(sum(row["share_pct"] for row in body["rows"]) - 100) <= 0.05


def test_by_environment_covers_all_three(client: TestClient) -> None:
    body = client.get("/api/cost/by-environment").json()
    environments = {row["environment"] for row in body["rows"]}
    assert environments == {"development", "staging", "production"}


def test_validation_unknown_environment_422(client: TestClient) -> None:
    response = client.get("/api/cost", params={"environment": "chaos"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["request_id"]


def test_validation_bad_granularity_422(client: TestClient) -> None:
    response = client.get("/api/cost/trend", params={"granularity": "year"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_validation_start_after_end_422(client: TestClient) -> None:
    response = client.get(
        "/api/cost", params={"start_date": "2026-08-01", "end_date": "2026-07-01"}
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert "start_date" in error["message"]


def test_validation_page_size_capped_422(client: TestClient) -> None:
    response = client.get("/api/cost", params={"page_size": 1000})
    assert response.status_code == 422


def test_validation_page_zero_422(client: TestClient) -> None:
    response = client.get("/api/cost", params={"page": 0})
    assert response.status_code == 422


def test_request_id_echoed(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-rid-123"})
    assert response.headers["x-request-id"] == "test-rid-123"


def test_request_id_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers.get("x-request-id")


def test_unknown_route_returns_structured_404(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "http_error"
    assert error["request_id"]


def test_cors_allows_configured_dashboard_origin(client: TestClient) -> None:
    """The Phase 2 dashboard (localhost:3000) calls the API cross-origin from the browser."""
    response = client.get("/api/cost/by-environment", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.get("/api/cost/by-environment", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers
