"""Tests for governance policies."""

import pytest
from app.governance.policies import (
    DevResourceSchedulePolicy,
    MaxMonthlyCostPolicy,
    NoPublicDatabasePolicy,
    RequireEnvironmentLabelPolicy,
    RequireOwnerLabelPolicy,
)
from app.main import app
from app.services.policy_service import PolicyService
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return PolicyService()


class TestRequireOwnerLabelPolicy:
    def test_pass_with_owner(self):
        policy = RequireOwnerLabelPolicy()
        resource = {"name": "test-vm", "owner": "rifky"}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_violation_no_owner(self):
        policy = RequireOwnerLabelPolicy()
        resource = {"name": "test-vm", "owner": None}
        result = policy.evaluate(resource)
        assert result["status"] == "VIOLATION"

    def test_violation_unallocated(self):
        policy = RequireOwnerLabelPolicy()
        resource = {"name": "test-vm", "owner": "UNALLOCATED"}
        result = policy.evaluate(resource)
        assert result["status"] == "VIOLATION"


class TestRequireEnvironmentLabelPolicy:
    def test_pass_production(self):
        policy = RequireEnvironmentLabelPolicy()
        resource = {"name": "test-vm", "environment": "production"}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_pass_staging(self):
        policy = RequireEnvironmentLabelPolicy()
        resource = {"name": "test-vm", "environment": "staging"}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_pass_development(self):
        policy = RequireEnvironmentLabelPolicy()
        resource = {"name": "test-vm", "environment": "development"}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_violation_no_environment(self):
        policy = RequireEnvironmentLabelPolicy()
        resource = {"name": "test-vm", "environment": None}
        result = policy.evaluate(resource)
        assert result["status"] == "VIOLATION"

    def test_violation_invalid_environment(self):
        policy = RequireEnvironmentLabelPolicy()
        resource = {"name": "test-vm", "environment": "testing"}
        result = policy.evaluate(resource)
        assert result["status"] == "VIOLATION"


class TestMaxMonthlyCostPolicy:
    def test_pass_dev_under_limit(self):
        policy = MaxMonthlyCostPolicy()
        resource = {"name": "test-vm", "environment": "development", "monthly_cost": 50.0}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_pass_dev_at_limit(self):
        policy = MaxMonthlyCostPolicy()
        resource = {"name": "test-vm", "environment": "development", "monthly_cost": 100.0}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_violation_dev_over_limit(self):
        policy = MaxMonthlyCostPolicy()
        resource = {"name": "test-vm", "environment": "development", "monthly_cost": 101.0}
        result = policy.evaluate(resource)
        assert result["status"] == "VIOLATION"

    def test_pass_staging_under_limit(self):
        policy = MaxMonthlyCostPolicy()
        resource = {"name": "test-vm", "environment": "staging", "monthly_cost": 150.0}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_warning_staging_over_limit(self):
        policy = MaxMonthlyCostPolicy()
        resource = {"name": "test-vm", "environment": "staging", "monthly_cost": 250.0}
        result = policy.evaluate(resource)
        assert result["status"] == "WARNING"

    def test_pass_production_high_cost(self):
        policy = MaxMonthlyCostPolicy()
        resource = {"name": "test-vm", "environment": "production", "monthly_cost": 500.0}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"


class TestNoPublicDatabasePolicy:
    def test_violation_public_database(self):
        policy = NoPublicDatabasePolicy()
        resource = {"name": "test-db", "service": "Cloud SQL", "public_access": True}
        result = policy.evaluate(resource)
        assert result["status"] == "VIOLATION"

    def test_pass_private_database(self):
        policy = NoPublicDatabasePolicy()
        resource = {"name": "test-db", "service": "Cloud SQL", "public_access": False}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_pass_public_compute(self):
        policy = NoPublicDatabasePolicy()
        resource = {"name": "test-vm", "service": "Compute Engine", "public_access": True}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"


class TestDevResourceSchedulePolicy:
    def test_warning_dev_compute_unscheduled(self):
        policy = DevResourceSchedulePolicy()
        resource = {"name": "test-vm", "environment": "development", "service": "Compute Engine", "scheduled": False}
        result = policy.evaluate(resource)
        assert result["status"] == "WARNING"

    def test_pass_dev_compute_scheduled(self):
        policy = DevResourceSchedulePolicy()
        resource = {"name": "test-vm", "environment": "development", "service": "Compute Engine", "scheduled": True}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_pass_dev_storage(self):
        policy = DevResourceSchedulePolicy()
        resource = {"name": "test-bucket", "environment": "development", "service": "Cloud Storage", "scheduled": False}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"

    def test_pass_production_compute_unscheduled(self):
        policy = DevResourceSchedulePolicy()
        resource = {"name": "test-vm", "environment": "production", "service": "Compute Engine", "scheduled": False}
        result = policy.evaluate(resource)
        assert result["status"] == "PASS"


class TestPolicyService:
    def test_evaluate_policies(self, service):
        result = service.evaluate_policies()
        assert "summary" in result
        assert "policies" in result
        assert "results" in result

    def test_summary_has_counts(self, service):
        result = service.evaluate_policies()
        summary = result["summary"]
        assert "total_resources" in summary
        assert "total_policies" in summary
        assert "violations" in summary
        assert "warnings" in summary
        assert "passed" in summary

    def test_policies_list(self, service):
        result = service.evaluate_policies()
        policies = result["policies"]
        assert len(policies) == 5
        for policy in policies:
            assert "name" in policy
            assert "description" in policy

    def test_results_per_resource(self, service):
        result = service.evaluate_policies()
        results = result["results"]
        assert len(results) == 8
        for r in results:
            assert "resource_id" in r
            assert "policy_results" in r


class TestPolicyAPI:
    def test_evaluate_policies(self, client):
        response = client.get("/api/policies")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "policies" in data
        assert "results" in data
