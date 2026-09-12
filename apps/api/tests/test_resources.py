"""Resource inventory tests (Phase 3).

The mock dataset has 12 resources across 4 projects / 4 services; the legacy
sandbox resource has no owner/team (UNALLOCATED scenario). Expected aggregates
are cross-checked against data/mock/cost.json where useful.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MOCK_DIR = Path(__file__).resolve().parents[3] / "data" / "mock"
TOLERANCE = 1e-6

EXPECTED_RESOURCES = 12
# Status counts in the dataset.
EXPECTED_STATUS: dict[str, int] = {"RUNNING": 7, "RUNNABLE": 2, "ACTIVE": 3}


def _expected_monthly_cost(resource_id: str) -> float:
    """Trailing-30-day gross cost from the committed dataset (independent recomputation)."""
    rows = json.loads((MOCK_DIR / "cost.json").read_text(encoding="utf-8"))
    end = max(date.fromisoformat(r["usage_date"]) for r in rows)
    start = end - timedelta(days=29)
    total = sum(
        Decimal(str(r["cost"]))
        for r in rows
        if r["resource_id"] == resource_id and start <= date.fromisoformat(r["usage_date"]) <= end
    )
    return round(float(total), 4)


def test_list_resources_pagination(client: TestClient) -> None:
    response = client.get("/api/resources", params={"page": 1, "page_size": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == EXPECTED_RESOURCES
    assert body["pagination"]["total_pages"] == (EXPECTED_RESOURCES + 4) // 5
    assert len(body["items"]) == 5
    assert body["window"] is not None
    assert body["summary"] is not None

    page3 = client.get("/api/resources", params={"page": 3, "page_size": 5}).json()
    assert len(page3["items"]) == 2  # 12 = 5 + 5 + 2

    beyond = client.get("/api/resources", params={"page": 4, "page_size": 5}).json()
    assert beyond["items"] == []

    # consecutive pages must not repeat resources
    page2 = client.get("/api/resources", params={"page": 2, "page_size": 5}).json()
    ids1 = {item["resource_id"] for item in body["items"]}
    ids2 = {item["resource_id"] for item in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_list_resources_ordered_by_monthly_cost_desc(client: TestClient) -> None:
    body = client.get("/api/resources", params={"page_size": 100}).json()
    costs = [item["monthly_cost"] for item in body["items"]]
    assert all(c is not None for c in costs)
    assert costs == sorted(costs, reverse=True)

    # the most expensive resource in the dataset is the production Cloud SQL
    top = body["items"][0]
    assert top["resource_id"] == "sql-shop-orders-prod"
    assert top["monthly_cost"] == pytest.approx(_expected_monthly_cost("sql-shop-orders-prod"))


def test_list_resources_fields_complete(client: TestClient) -> None:
    body = client.get("/api/resources", params={"page_size": 100}).json()
    required = {
        "resource_id",
        "resource_name",
        "resource_type",
        "service_id",
        "service_name",
        "project_id",
        "project_name",
        "region",
        "zone",
        "status",
        "environment",
        "machine_type",
        "owner",
        "team",
        "application",
        "labels",
        "created_at",
        "last_seen",
        "monthly_cost",
        "monthly_credits",
        "monthly_net_cost",
        "cpu_utilization",
        "memory_utilization",
        "potential_saving",
    }
    for item in body["items"]:
        assert required <= set(item.keys()), f"missing fields: {required - set(item.keys())}"
        # Phase 3 contract: potential saving stays null until Phase 4 exists.
        assert item["potential_saving"] is None


def test_list_resources_latest_utilization_attached(client: TestClient) -> None:
    """The latest utilization sample joins onto the list; resources without the
    metric (storage buckets) stay null — never zero, never guessed."""
    usage_rows = json.loads((MOCK_DIR / "usage.json").read_text(encoding="utf-8"))
    latest = max(
        (r for r in usage_rows if r["resource_id"] == "vm-shop-api-prod-1"),
        key=lambda r: r["usage_date"],
    )
    body = client.get("/api/resources").json()
    item = next(i for i in body["items"] if i["resource_id"] == "vm-shop-api-prod-1")
    assert item["cpu_utilization"] == latest["cpu_utilization"]
    assert item["memory_utilization"] == latest["memory_utilization"]

    bucket = next(i for i in body["items"] if i["resource_id"] == "gcs-shop-assets-prod")
    assert bucket["cpu_utilization"] is None


def test_filter_by_service(client: TestClient) -> None:
    body = client.get(
        "/api/resources", params={"service": "compute-engine", "page_size": 100}
    ).json()
    assert body["pagination"]["total_items"] == 7
    assert all(item["service_id"] == "compute-engine" for item in body["items"])


def test_filter_by_project(client: TestClient) -> None:
    body = client.get(
        "/api/resources", params={"project_id": "cc-lab-shop-prod", "page_size": 100}
    ).json()
    assert body["pagination"]["total_items"] == 6
    assert all(item["project_id"] == "cc-lab-shop-prod" for item in body["items"])


def test_filter_by_environment(client: TestClient) -> None:
    body = client.get("/api/resources", params={"environment": "staging", "page_size": 100}).json()
    assert body["pagination"]["total_items"] == 3
    assert all(item["environment"] == "staging" for item in body["items"])


def test_filter_by_status(client: TestClient) -> None:
    for status, expected in EXPECTED_STATUS.items():
        body = client.get("/api/resources", params={"status": status, "page_size": 100}).json()
        assert body["pagination"]["total_items"] == expected, status
        assert all(item["status"] == status for item in body["items"])


def test_filter_by_owner_and_team(client: TestClient) -> None:
    by_owner = client.get("/api/resources", params={"owner": "rifky", "page_size": 100}).json()
    assert by_owner["pagination"]["total_items"] == 11  # everyone except the legacy sandbox

    by_team = client.get("/api/resources", params={"team": "platform", "page_size": 100}).json()
    assert by_team["pagination"]["total_items"] == 11

    unknown = client.get("/api/resources", params={"owner": "nobody", "page_size": 100}).json()
    assert unknown["items"] == []
    assert unknown["pagination"]["total_items"] == 0


def test_filter_by_region(client: TestClient) -> None:
    body = client.get(
        "/api/resources", params={"region": "asia-southeast2", "page_size": 100}
    ).json()
    assert body["pagination"]["total_items"] == 3  # staging resources
    assert all(item["region"] == "asia-southeast2" for item in body["items"])


def test_filter_unallocated(client: TestClient) -> None:
    body = client.get("/api/resources", params={"unallocated": "true", "page_size": 100}).json()
    assert body["pagination"]["total_items"] == 1
    item = body["items"][0]
    assert item["resource_id"] == "vm-legacy-sandbox-1"
    assert item["owner"] is None and item["team"] is None and item["application"] is None
    # monthly cost still tracked even without attribution
    assert item["monthly_cost"] > 0


def test_combined_filters_intersect(client: TestClient) -> None:
    body = client.get(
        "/api/resources",
        params={"service": "compute-engine", "environment": "production", "page_size": 100},
    ).json()
    assert body["pagination"]["total_items"] == 3
    assert all(
        item["service_id"] == "compute-engine" and item["environment"] == "production"
        for item in body["items"]
    )


def test_list_resources_empty_result_is_200(client: TestClient) -> None:
    response = client.get("/api/resources", params={"project_id": "no-such-project"})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["pagination"]["total_items"] == 0
    assert body["summary"] is not None and body["summary"]["monthly_cost"] == 0.0


def test_list_resources_summary_covers_filtered_set(client: TestClient) -> None:
    """Summary must cover the whole filtered set, not only the current page."""
    body = client.get("/api/resources", params={"page_size": 5}).json()
    assert body["pagination"]["total_pages"] > 1
    expected = sum(
        _expected_monthly_cost(item["resource_id"]) for item in body["items"]
    )  # only a page
    assert body["summary"]["monthly_cost"] > expected  # full set must be larger than one page
    full = client.get("/api/resources", params={"page_size": 100}).json()
    expected_full = sum(_expected_monthly_cost(item["resource_id"]) for item in full["items"])
    assert body["summary"]["monthly_cost"] == pytest.approx(round(expected_full, 4))


def test_resource_detail(client: TestClient) -> None:
    response = client.get("/api/resources/vm-shop-api-prod-1")
    assert response.status_code == 200
    body = response.json()
    assert body["resource_id"] == "vm-shop-api-prod-1"
    assert body["service_name"] == "Compute Engine"
    assert body["project_name"] == "Shop Platform — Production"
    assert body["environment"] == "production"
    assert body["zone"] == "us-central1-a"
    assert body["machine_type"] == "e2-standard-2"
    assert body["owner"] == "rifky" and body["team"] == "platform"

    # cost history covers the full dataset range; monthly = trailing 30 days
    assert len(body["cost_history"]) == 97
    assert body["monthly_cost"] == pytest.approx(_expected_monthly_cost("vm-shop-api-prod-1"))
    assert body["total_cost"] == pytest.approx(_expected_total_cost("vm-shop-api-prod-1"))

    # utilization series with the latest values echoed at the top level
    assert len(body["utilization"]) == 97
    assert body["cpu_utilization"] == body["utilization"][-1]["cpu_utilization"]
    assert body["memory_utilization"] == body["utilization"][-1]["memory_utilization"]
    assert body["potential_saving"] is None


def _expected_total_cost(resource_id: str) -> float:
    rows = json.loads((MOCK_DIR / "cost.json").read_text(encoding="utf-8"))
    return round(
        float(sum(Decimal(str(r["cost"])) for r in rows if r["resource_id"] == resource_id)), 4
    )


def test_resource_detail_unallocated(client: TestClient) -> None:
    """Ownership gaps must be surfaced as nulls (rendered UNALLOCATED), never guessed."""
    response = client.get("/api/resources/vm-legacy-sandbox-1")
    assert response.status_code == 200
    body = response.json()
    assert body["owner"] is None
    assert body["team"] is None
    assert body["application"] is None
    assert body["labels"].get("team") is None
    assert body["labels"].get("environment") == "development"  # env attribution still present


def test_resource_detail_invalid_id_404(client: TestClient) -> None:
    response = client.get("/api/resources/vm-does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "http_error"
    assert "vm-does-not-exist" in error["message"]
    assert error["request_id"]


def test_idle_vm_latest_utilization_is_low(client: TestClient) -> None:
    """Scenario data check: the idle dev VM must show CPU < 5% (Phase 4 evidence)."""
    body = client.get("/api/resources/vm-report-dev-1").json()
    assert body["cpu_utilization"] is not None
    assert body["cpu_utilization"] < 5.0


def test_validation_page_zero_rejected(client: TestClient) -> None:
    response = client.get("/api/resources", params={"page": 0})
    assert response.status_code == 422


def test_validation_unknown_environment_rejected(client: TestClient) -> None:
    response = client.get("/api/resources", params={"environment": "chaos"})
    assert response.status_code == 422


def test_resource_detail_storage_bucket_has_no_cpu_series(client: TestClient) -> None:
    detail = client.get("/api/resources/gcs-shop-assets-prod").json()
    assert detail["cpu_utilization"] is None
    assert detail["memory_utilization"] is None
    # Storage exposes network + request metrics instead of compute utilization.
    assert any(point["network_in_mb"] is not None for point in detail["utilization"])
    assert any(point["request_count"] is not None for point in detail["utilization"])
