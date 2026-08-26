"""Tests for resource inventory API and service."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.resource_service import ResourceService
from app.services.mock_data import RESOURCES


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return ResourceService()


class TestResourceService:
    def test_list_all_resources(self, service):
        result = service.list_resources()
        assert result["total"] == len(RESOURCES)
        assert len(result["data"]) == len(RESOURCES)
        assert result["page"] == 1

    def test_pagination(self, service):
        result = service.list_resources(page=1, page_size=3)
        assert result["total"] == len(RESOURCES)
        assert len(result["data"]) == 3
        assert result["page"] == 1
        assert result["page_size"] == 3
        assert result["total_pages"] == 3

    def test_pagination_last_page(self, service):
        result = service.list_resources(page=3, page_size=3)
        assert len(result["data"]) == 2
        assert result["page"] == 3

    def test_filter_by_environment(self, service):
        result = service.list_resources(environment="production")
        for r in result["data"]:
            assert r["environment"] == "production"
        assert result["total"] >= 1

    def test_filter_by_project(self, service):
        result = service.list_resources(project="cloud-cost-lab-prod")
        for r in result["data"]:
            assert r["project"] == "cloud-cost-lab-prod"

    def test_filter_by_service(self, service):
        result = service.list_resources(service="compute-engine")
        for r in result["data"]:
            assert r["service"] == "Compute Engine"

    def test_filter_by_owner(self, service):
        result = service.list_resources(owner="UNALLOCATED")
        assert result["total"] == 1
        assert result["data"][0]["owner"] == "UNALLOCATED"

    def test_filter_by_team(self, service):
        result = service.list_resources(team="platform")
        for r in result["data"]:
            assert r["team"] == "platform"

    def test_filter_no_results(self, service):
        result = service.list_resources(project="nonexistent")
        assert result["total"] == 0
        assert result["data"] == []
        assert result["total_pages"] == 1

    def test_resource_has_required_fields(self, service):
        result = service.list_resources()
        for r in result["data"]:
            assert "resource_id" in r
            assert "name" in r
            assert "type" in r
            assert "project" in r
            assert "service" in r
            assert "region" in r
            assert "environment" in r
            assert "status" in r
            assert "owner" in r
            assert "team" in r
            assert "monthly_cost" in r
            assert "cpu_utilization" in r
            assert "memory_utilization" in r
            assert "potential_saving" in r

    def test_get_resource_detail(self, service):
        result = service.get_resource("vm-prod-api-01")
        assert result is not None
        assert result["resource_id"] == "vm-prod-api-01"
        assert result["monthly_cost"] > 0
        assert "utilization" in result
        assert "utilization_history" in result
        assert "cost_history" in result
        assert "labels" in result
        assert "created_at" in result
        assert "last_seen" in result

    def test_get_resource_not_found(self, service):
        result = service.get_resource("nonexistent-resource")
        assert result is None

    def test_unallocated_resource(self, service):
        result = service.get_resource("vm-idle-01")
        assert result is not None
        assert result["owner"] == "UNALLOCATED"
        assert result["team"] == "UNALLOCATED"
        assert result["application"] == "UNALLOCATED"
        assert result["labels"] == {}

    def test_resource_cost_history_has_data(self, service):
        result = service.get_resource("vm-prod-api-01")
        assert len(result["cost_history"]) > 0
        for entry in result["cost_history"]:
            assert "date" in entry
            assert "cost" in entry
            assert entry["cost"] > 0

    def test_resource_utilization_history(self, service):
        result = service.get_resource("vm-prod-api-01")
        assert len(result["utilization_history"]) > 0
        for entry in result["utilization_history"]:
            assert "date" in entry
            assert "cpu_utilization" in entry
            assert "memory_utilization" in entry

    def test_storage_resource_no_cpu(self, service):
        result = service.get_resource("gcs-prod-assets")
        assert result["utilization"]["cpu_avg"] is None
        assert result["utilization"]["memory_avg"] is None
        assert result["utilization"]["disk_avg"] is not None


class TestResourceAPI:
    def test_list_resources(self, client):
        response = client.get("/api/resources")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_list_with_pagination(self, client):
        response = client.get("/api/resources?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["page"] == 1

    def test_list_filter_environment(self, client):
        response = client.get("/api/resources?environment=production")
        assert response.status_code == 200
        data = response.json()
        for r in data["data"]:
            assert r["environment"] == "production"

    def test_list_filter_no_results(self, client):
        response = client.get("/api/resources?project=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["data"] == []

    def test_get_resource_detail(self, client):
        response = client.get("/api/resources/vm-prod-api-01")
        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == "vm-prod-api-01"
        assert data["monthly_cost"] > 0
        assert "utilization_history" in data
        assert "cost_history" in data

    def test_get_resource_not_found(self, client):
        response = client.get("/api/resources/does-not-exist")
        assert response.status_code == 404

    def test_invalid_page_size(self, client):
        response = client.get("/api/resources?page_size=200")
        assert response.status_code == 422

    def test_invalid_page_zero(self, client):
        response = client.get("/api/resources?page=0")
        assert response.status_code == 422
