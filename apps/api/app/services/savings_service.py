"""Savings tracking and recommendation lifecycle service.

Manages the lifecycle: OPEN → APPROVED → IMPLEMENTED → VERIFIED
Supports: REJECTED at any stage.

Distinguishes:
- Potential savings: estimated before action
- Realized savings: verified after action with actual before/after data

Does NOT call simulated savings "realized".
"""

from datetime import datetime
from typing import Optional

from app.services.recommendation_service import recommendation_service

_LIFECYCLE_FIELDS = (
    "status",
    "approved_at",
    "approved_by",
    "implemented_at",
    "implemented_by",
    "verified_at",
    "rejected_at",
    "rejected_by",
    "rejection_reason",
    "cost_before",
    "cost_after",
    "realized_savings",
)


class SavingsService:
    def __init__(self):
        self._recommendations_state: dict[str, dict] = {}
        self._audit_log: list[dict] = []
        self._persister = None
        self._seed_demo_data()

    def _seed_demo_data(self):
        """Seed some recommendations in various lifecycle states for demo."""
        recs = recommendation_service.generate_recommendations()
        if not recs:
            return

        # Leave the last recommendation OPEN so approval can still be exercised.
        # First recommendation: VERIFIED (realized savings)
        if len(recs) > 1:
            rec = recs[0]
            self._recommendations_state[rec["id"]] = {
                **rec,
                "status": "VERIFIED",
                "approved_at": "2026-08-10T14:00:00Z",
                "approved_by": "rifky",
                "implemented_at": "2026-08-12T09:30:00Z",
                "implemented_by": "rifky",
                "verified_at": "2026-08-20T10:00:00Z",
                "cost_before": rec["current_cost"],
                "cost_after": rec["potential_cost"],
                "realized_savings": round(rec["current_cost"] - rec["potential_cost"], 2),
            }
            self._audit_log.append({"timestamp": "2026-08-10T14:00:00Z", "action": "APPROVED", "recommendation_id": rec["id"], "actor": "rifky"})
            self._audit_log.append({"timestamp": "2026-08-12T09:30:00Z", "action": "IMPLEMENTED", "recommendation_id": rec["id"], "actor": "rifky"})
            self._audit_log.append({"timestamp": "2026-08-20T10:00:00Z", "action": "VERIFIED", "recommendation_id": rec["id"], "actor": "system"})

        # Second recommendation: IMPLEMENTED (awaiting verification)
        if len(recs) > 2:
            rec = recs[1]
            self._recommendations_state[rec["id"]] = {
                **rec,
                "status": "IMPLEMENTED",
                "approved_at": "2026-08-15T11:00:00Z",
                "approved_by": "rifky",
                "implemented_at": "2026-08-18T16:00:00Z",
                "implemented_by": "rifky",
                "verified_at": None,
                "cost_before": rec["current_cost"],
                "cost_after": None,
                "realized_savings": None,
            }
            self._audit_log.append({"timestamp": "2026-08-15T11:00:00Z", "action": "APPROVED", "recommendation_id": rec["id"], "actor": "rifky"})
            self._audit_log.append({"timestamp": "2026-08-18T16:00:00Z", "action": "IMPLEMENTED", "recommendation_id": rec["id"], "actor": "rifky"})

        # Third recommendation: APPROVED (not yet implemented)
        if len(recs) > 3:
            rec = recs[2]
            self._recommendations_state[rec["id"]] = {
                **rec,
                "status": "APPROVED",
                "approved_at": "2026-08-22T09:00:00Z",
                "approved_by": "rifky",
                "implemented_at": None,
                "implemented_by": None,
                "verified_at": None,
                "cost_before": None,
                "cost_after": None,
                "realized_savings": None,
            }
            self._audit_log.append({"timestamp": "2026-08-22T09:00:00Z", "action": "APPROVED", "recommendation_id": rec["id"], "actor": "rifky"})

        # Fourth recommendation: REJECTED
        if len(recs) > 4:
            rec = recs[3]
            self._recommendations_state[rec["id"]] = {
                **rec,
                "status": "REJECTED",
                "rejected_at": "2026-08-20T15:00:00Z",
                "rejected_by": "rifky",
                "rejection_reason": "Resource is needed for upcoming load test",
            }
            self._audit_log.append({"timestamp": "2026-08-20T15:00:00Z", "action": "REJECTED", "recommendation_id": rec["id"], "actor": "rifky", "reason": "Resource is needed for upcoming load test"})

    def list_recommendations(
        self,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """Return engine recommendations overlaid with this lifecycle store."""
        recommendations = recommendation_service.generate_recommendations(start_date, end_date)
        return [self._with_lifecycle(recommendation) for recommendation in recommendations]

    def get_recommendation_state(self, rec_id: str) -> Optional[dict]:
        """Get the current lifecycle state of a recommendation."""
        recommendation = recommendation_service.get_recommendation(rec_id)
        if recommendation is not None:
            return self._with_lifecycle(recommendation)
        return self._recommendations_state.get(rec_id)

    def _with_lifecycle(self, recommendation: dict) -> dict:
        state = self._recommendations_state.get(recommendation["id"])
        if state is None:
            return recommendation
        merged = dict(recommendation)
        for field in _LIFECYCLE_FIELDS:
            if field in state:
                merged[field] = state[field]
        return merged

    def _persist(self) -> None:
        if self._persister is not None:
            self._persister.sync(self)

    def approve(self, rec_id: str, actor: str) -> dict:
        """Approve a recommendation for implementation."""
        actor = _require_principal_name(actor)
        rec = self._get_or_create_state(rec_id)
        if rec is None:
            raise ValueError(f"Recommendation '{rec_id}' not found")
        if rec["status"] != "OPEN":
            raise ValueError(f"Cannot approve: current status is '{rec['status']}' (must be OPEN)")

        now = datetime(2026, 8, 26, 12, 0, 0).isoformat() + "Z"
        rec["status"] = "APPROVED"
        rec["approved_at"] = now
        rec["approved_by"] = actor
        self._recommendations_state[rec_id] = rec
        self._audit_log.append({"timestamp": now, "action": "APPROVED", "recommendation_id": rec_id, "actor": actor})
        self._persist()
        return rec

    def reject(self, rec_id: str, actor: str, reason: str) -> dict:
        """Reject a recommendation."""
        actor = _require_principal_name(actor)
        reason = _require_reason(reason)
        rec = self._get_or_create_state(rec_id)
        if rec is None:
            raise ValueError(f"Recommendation '{rec_id}' not found")
        if rec["status"] in ["VERIFIED", "REJECTED"]:
            raise ValueError(f"Cannot reject: current status is '{rec['status']}'")

        now = datetime(2026, 8, 26, 12, 0, 0).isoformat() + "Z"
        rec["status"] = "REJECTED"
        rec["rejected_at"] = now
        rec["rejected_by"] = actor
        rec["rejection_reason"] = reason
        self._recommendations_state[rec_id] = rec
        self._audit_log.append({"timestamp": now, "action": "REJECTED", "recommendation_id": rec_id, "actor": actor, "reason": reason})
        self._persist()
        return rec

    def implement(self, rec_id: str, actor: str) -> dict:
        """Mark a recommendation as implemented."""
        actor = _require_principal_name(actor)
        rec = self._get_or_create_state(rec_id)
        if rec is None:
            raise ValueError(f"Recommendation '{rec_id}' not found")
        if rec["status"] != "APPROVED":
            raise ValueError(f"Cannot implement: current status is '{rec['status']}' (must be APPROVED)")

        now = datetime(2026, 8, 26, 12, 0, 0).isoformat() + "Z"
        rec["status"] = "IMPLEMENTED"
        rec["implemented_at"] = now
        rec["implemented_by"] = actor
        rec["cost_before"] = rec["current_cost"]
        self._recommendations_state[rec_id] = rec
        self._audit_log.append({"timestamp": now, "action": "IMPLEMENTED", "recommendation_id": rec_id, "actor": actor})
        self._persist()
        return rec

    def verify(self, rec_id: str, cost_after: float) -> dict:
        """Verify savings with actual post-change cost data."""
        if cost_after < 0 or cost_after != cost_after or cost_after == float("inf"):
            raise ValueError("cost_after must be >= 0")
        rec = self._get_or_create_state(rec_id)
        if rec is None:
            raise ValueError(f"Recommendation '{rec_id}' not found")
        if rec["status"] != "IMPLEMENTED":
            raise ValueError(f"Cannot verify: current status is '{rec['status']}' (must be IMPLEMENTED)")

        now = datetime(2026, 8, 26, 12, 0, 0).isoformat() + "Z"
        cost_before = rec.get("cost_before", rec["current_cost"])
        realized = round(cost_before - cost_after, 2)

        rec["status"] = "VERIFIED"
        rec["verified_at"] = now
        rec["cost_after"] = cost_after
        rec["realized_savings"] = realized
        self._recommendations_state[rec_id] = rec
        self._audit_log.append({"timestamp": now, "action": "VERIFIED", "recommendation_id": rec_id, "actor": "system", "cost_before": cost_before, "cost_after": cost_after, "realized_savings": realized})
        self._persist()
        return rec

    def get_savings_summary(self) -> dict:
        """Get savings summary across all tracked recommendations."""
        published = self.list_recommendations()
        open_recs = [r for r in published if r["status"] == "OPEN"]
        all_recs = published

        potential_savings = sum(r["potential_savings"] for r in open_recs)
        approved_savings = sum(r["potential_savings"] for r in all_recs if r["status"] == "APPROVED")
        implemented_savings = sum(r["potential_savings"] for r in all_recs if r["status"] == "IMPLEMENTED")
        realized_savings = sum(r.get("realized_savings", 0) or 0 for r in all_recs if r["status"] == "VERIFIED")
        rejected_count = sum(1 for r in all_recs if r["status"] == "REJECTED")

        return {
            "potential": {
                "count": len(open_recs),
                "total_savings": round(potential_savings, 2),
                "label": "Estimated savings if all open recommendations are implemented",
            },
            "approved": {
                "count": sum(1 for r in all_recs if r["status"] == "APPROVED"),
                "total_savings": round(approved_savings, 2),
                "label": "Approved, awaiting implementation",
            },
            "implemented": {
                "count": sum(1 for r in all_recs if r["status"] == "IMPLEMENTED"),
                "total_savings": round(implemented_savings, 2),
                "label": "Implemented, awaiting verification with actual data",
            },
            "verified": {
                "count": sum(1 for r in all_recs if r["status"] == "VERIFIED"),
                "total_savings": round(realized_savings, 2),
                "label": "Verified with actual before/after cost data (REALIZED)",
            },
            "rejected": {
                "count": rejected_count,
            },
            "total_realized_savings": round(realized_savings, 2),
            "total_potential_savings": round(potential_savings + approved_savings + implemented_savings, 2),
        }

    def get_audit_log(self) -> list[dict]:
        """Get the full audit log of lifecycle transitions."""
        return list(reversed(self._audit_log))

    def _get_or_create_state(self, rec_id: str) -> Optional[dict]:
        """Get existing state or initialize from recommendation engine."""
        if rec_id in self._recommendations_state:
            return self._recommendations_state[rec_id]
        rec = recommendation_service.get_recommendation(rec_id)
        if rec is None:
            return None
        self._recommendations_state[rec_id] = rec
        return rec


def _require_principal_name(actor: str) -> str:
    cleaned = actor.strip()
    if not cleaned or len(cleaned) > 100:
        raise ValueError("Principal is required")
    return cleaned


def _require_reason(reason: str) -> str:
    cleaned = reason.strip()
    if not cleaned or len(cleaned) > 500:
        raise ValueError("Reason must be 1-500 characters")
    return cleaned


savings_service = SavingsService()
