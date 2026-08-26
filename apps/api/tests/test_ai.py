"""Tests for AI Cloud Cost Advisor."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.advisor import CostAdvisor
from app.ai.safety import sanitize_input, validate_question, filter_sensitive_data


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def advisor():
    return CostAdvisor()


class TestAISafety:
    def test_sanitize_removes_control_chars(self):
        result = sanitize_input("hello\x00world\x01")
        assert "\x00" not in result
        assert "\x01" not in result
        assert "helloworld" in result

    def test_sanitize_limits_length(self):
        long_input = "a" * 2000
        result = sanitize_input(long_input)
        assert len(result) == 1000

    def test_validate_rejects_destructive(self):
        is_valid, _ = validate_question("delete all my resources")
        assert is_valid is False

    def test_validate_rejects_terraform_destroy(self):
        is_valid, _ = validate_question("run terraform destroy on production")
        assert is_valid is False

    def test_validate_rejects_iam_modification(self):
        is_valid, _ = validate_question("modify iam policy for billing account")
        assert is_valid is False

    def test_validate_accepts_cost_question(self):
        is_valid, _ = validate_question("Why did my cost increase this month?")
        assert is_valid is True

    def test_validate_rejects_too_short(self):
        is_valid, _ = validate_question("hi")
        assert is_valid is False

    def test_filter_sensitive_data(self):
        data = {
            "cost": 100.0,
            "service_account_key": "secret-key-123",
            "private_key": "-----BEGIN RSA-----",
            "project": "my-project",
        }
        filtered = filter_sensitive_data(data)
        assert "cost" in filtered
        assert "project" in filtered
        assert "service_account_key" not in filtered
        assert "private_key" not in filtered

    def test_filter_nested(self):
        data = {
            "config": {
                "api_key": "secret",
                "endpoint": "https://api.example.com",
            }
        }
        filtered = filter_sensitive_data(data)
        assert "endpoint" in filtered["config"]
        assert "api_key" not in filtered["config"]


class TestCostAdvisor:
    def test_cost_increase_question(self, advisor):
        result = advisor.analyze("Why did cost increase this month?")
        assert "summary" in result
        assert "evidence" in result
        assert "confidence" in result
        assert "safety_note" in result
        assert "read-only" in result["safety_note"].lower()

    def test_savings_question(self, advisor):
        result = advisor.analyze("Where can I save money?")
        assert "summary" in result
        assert "potential_savings" in result
        assert result["potential_savings"] is not None

    def test_idle_resource_question(self, advisor):
        result = advisor.analyze("Which resource is idle or unused?")
        assert "summary" in result
        assert "evidence" in result

    def test_anomaly_question(self, advisor):
        result = advisor.analyze("What caused the cost anomaly?")
        assert "summary" in result
        assert "confidence" in result

    def test_forecast_question(self, advisor):
        result = advisor.analyze("What is my cost forecast for next month?")
        assert "summary" in result
        assert "evidence" in result

    def test_priority_question(self, advisor):
        result = advisor.analyze("Which recommendation has the highest priority?")
        assert "summary" in result
        assert "recommendation" in result

    def test_budget_question(self, advisor):
        result = advisor.analyze("What is my budget status?")
        assert "summary" in result
        assert "budget" in result["summary"].lower() or "Budget" in result["summary"]

    def test_general_question(self, advisor):
        result = advisor.analyze("Give me an overview of my cloud costs")
        assert "summary" in result
        assert "evidence" in result

    def test_destructive_question_rejected(self, advisor):
        result = advisor.analyze("delete all idle VMs")
        assert "Cannot process" in result["summary"]
        assert "destructive" in result["evidence"].lower()

    def test_always_includes_safety_note(self, advisor):
        result = advisor.analyze("Where can I save money?")
        assert "safety_note" in result
        assert "read-only" in result["safety_note"].lower()

    def test_insufficient_data_handling(self, advisor):
        result = advisor.analyze("What is my cost forecast for next month?")
        # Should either provide a forecast or say "insufficient evidence"
        assert result["summary"] is not None
        if "insufficient" in result["summary"].lower():
            assert result["confidence"] == "LOW"


class TestAIAPI:
    def test_ask_endpoint(self, client):
        response = client.post("/api/ai/ask", json={"question": "Where can I save money?"})
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "evidence" in data
        assert "safety_note" in data

    def test_ask_with_reference_date(self, client):
        response = client.post(
            "/api/ai/ask?reference_date=2026-08-20",
            json={"question": "Why did cost increase?"},
        )
        assert response.status_code == 200

    def test_ask_too_short(self, client):
        response = client.post("/api/ai/ask", json={"question": "hi"})
        assert response.status_code == 422

    def test_capabilities_endpoint(self, client):
        response = client.get("/api/ai/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "READ-ONLY"
        assert "capabilities" in data
        assert "cannot_do" in data
        assert "safety" in data
        assert data["safety"]["read_only"] is True
