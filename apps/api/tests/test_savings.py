"""Tests for savings verification workflow and recommendation lifecycle."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.savings_service import SavingsService
from app.services.recommendation_service import recommendation_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return SavingsService()


@pytest.fixture
def fresh_service():
    """Service without demo seed data."""
    svc = SavingsService()
    svc._recommendations_state.clear()
    svc._audit_log.clear()
    return svc


@pytest.fixture
def open_rec_id():
    """Get an ID of a recommendation that should be in OPEN state."""
    recs = recommendation_service.generate_recommendations()
    svc = SavingsService()
    tracked_ids = set(svc._recommendations_state.keys())
    for r in recs:
        if r["id"] not in tracked_ids:
            return r["id"]
    return None


class TestSavingsLifecycle:
    def test_approve_open_recommendation(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        result = fresh_service.approve(rec_id, "engineer")
        assert result["status"] == "APPROVED"
        assert result["approved_by"] == "engineer"
        assert result["approved_at"] is not None

    def test_cannot_approve_non_open(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        fresh_service.approve(rec_id, "engineer")
        with pytest.raises(ValueError, match="must be OPEN"):
            fresh_service.approve(rec_id, "engineer")

    def test_reject_recommendation(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        result = fresh_service.reject(rec_id, "manager", "Not needed right now")
        assert result["status"] == "REJECTED"
        assert result["rejected_by"] == "manager"
        assert result["rejection_reason"] == "Not needed right now"

    def test_cannot_reject_verified(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        fresh_service.approve(rec_id, "eng")
        fresh_service.implement(rec_id, "eng")
        fresh_service.verify(rec_id, 5.0)
        with pytest.raises(ValueError, match="Cannot reject"):
            fresh_service.reject(rec_id, "mgr", "too late")

    def test_implement_approved(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        fresh_service.approve(rec_id, "eng")
        result = fresh_service.implement(rec_id, "eng")
        assert result["status"] == "IMPLEMENTED"
        assert result["implemented_by"] == "eng"
        assert result["cost_before"] == recs[0]["current_cost"]

    def test_cannot_implement_open(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        with pytest.raises(ValueError, match="must be APPROVED"):
            fresh_service.implement(rec_id, "eng")

    def test_verify_with_actual_cost(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        cost_before = recs[0]["current_cost"]
        fresh_service.approve(rec_id, "eng")
        fresh_service.implement(rec_id, "eng")
        result = fresh_service.verify(rec_id, 5.0)
        assert result["status"] == "VERIFIED"
        assert result["cost_after"] == 5.0
        assert result["realized_savings"] == round(cost_before - 5.0, 2)

    def test_cannot_verify_non_implemented(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        fresh_service.approve(rec_id, "eng")
        with pytest.raises(ValueError, match="must be IMPLEMENTED"):
            fresh_service.verify(rec_id, 5.0)

    def test_full_lifecycle(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        cost_before = recs[0]["current_cost"]

        state = fresh_service.get_recommendation_state(rec_id)
        assert state["status"] == "OPEN"

        fresh_service.approve(rec_id, "eng")
        state = fresh_service.get_recommendation_state(rec_id)
        assert state["status"] == "APPROVED"

        fresh_service.implement(rec_id, "eng")
        state = fresh_service.get_recommendation_state(rec_id)
        assert state["status"] == "IMPLEMENTED"
        assert state["cost_before"] == cost_before

        fresh_service.verify(rec_id, 3.0)
        state = fresh_service.get_recommendation_state(rec_id)
        assert state["status"] == "VERIFIED"
        assert state["realized_savings"] == round(cost_before - 3.0, 2)

    def test_nonexistent_recommendation(self, fresh_service):
        with pytest.raises(ValueError, match="not found"):
            fresh_service.approve("nonexistent", "eng")

    def test_before_after_calculation(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        cost_before = recs[0]["current_cost"]
        cost_after = 2.50

        fresh_service.approve(rec_id, "eng")
        fresh_service.implement(rec_id, "eng")
        result = fresh_service.verify(rec_id, cost_after)

        assert result["cost_before"] == cost_before
        assert result["cost_after"] == cost_after
        assert result["realized_savings"] == round(cost_before - cost_after, 2)


class TestSavingsSummary:
    def test_summary_structure(self, service):
        summary = service.get_savings_summary()
        assert "potential" in summary
        assert "approved" in summary
        assert "implemented" in summary
        assert "verified" in summary
        assert "rejected" in summary
        assert "total_realized_savings" in summary
        assert "total_potential_savings" in summary

    def test_potential_label(self, service):
        summary = service.get_savings_summary()
        assert "Estimated" in summary["potential"]["label"]

    def test_verified_label(self, service):
        summary = service.get_savings_summary()
        assert "REALIZED" in summary["verified"]["label"]

    def test_realized_only_for_verified(self, service):
        summary = service.get_savings_summary()
        assert summary["total_realized_savings"] >= 0
        # Only VERIFIED recommendations contribute to realized
        verified_count = summary["verified"]["count"]
        if verified_count == 0:
            assert summary["total_realized_savings"] == 0


class TestAuditLog:
    def test_audit_log_populated(self, service):
        log = service.get_audit_log()
        assert len(log) > 0

    def test_audit_log_has_fields(self, service):
        log = service.get_audit_log()
        for entry in log:
            assert "timestamp" in entry
            assert "action" in entry
            assert "recommendation_id" in entry
            assert "actor" in entry

    def test_audit_log_on_action(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        fresh_service.approve(rec_id, "test-user")
        log = fresh_service.get_audit_log()
        assert len(log) == 1
        assert log[0]["action"] == "APPROVED"
        assert log[0]["actor"] == "test-user"

    def test_audit_log_reject_has_reason(self, fresh_service):
        recs = recommendation_service.generate_recommendations()
        rec_id = recs[0]["id"]
        fresh_service.reject(rec_id, "mgr", "not needed")
        log = fresh_service.get_audit_log()
        assert log[0]["reason"] == "not needed"


class TestSavingsAPI:
    def test_get_savings_summary(self, client):
        response = client.get("/api/savings")
        assert response.status_code == 200
        data = response.json()
        assert "potential" in data
        assert "verified" in data
        assert "total_realized_savings" in data

    def test_get_audit_log(self, client):
        response = client.get("/api/savings/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert "audit_log" in data
        assert "total" in data

    def test_get_recommendation_state(self, client):
        recs_response = client.get("/api/recommendations")
        recs = recs_response.json()["recommendations"]
        if recs:
            rec_id = recs[0]["id"]
            response = client.get(f"/api/savings/{rec_id}")
            assert response.status_code == 200

    def test_recommendation_not_found(self, client):
        response = client.get("/api/savings/nonexistent")
        assert response.status_code == 404

    def test_approve_endpoint(self, client, open_rec_id):
        if open_rec_id is None:
            pytest.skip("No open recommendation available")
        response = client.post(
            f"/api/savings/{open_rec_id}/approve",
            json={"actor": "test-user"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"

    def test_reject_endpoint(self, client):
        recs_response = client.get("/api/recommendations")
        recs = recs_response.json()["recommendations"]
        svc = SavingsService()
        tracked = set(svc._recommendations_state.keys())
        open_recs = [r for r in recs if r["id"] not in tracked]
        if not open_recs:
            pytest.skip("No open recommendation")
        rec_id = open_recs[-1]["id"]
        response = client.post(
            f"/api/savings/{rec_id}/reject",
            json={"actor": "mgr", "reason": "not needed"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"
