from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.savings_service import savings_service

router = APIRouter(prefix="/api/savings", tags=["savings"])


class ApproveRequest(BaseModel):
    actor: str


class RejectRequest(BaseModel):
    actor: str
    reason: str


class ImplementRequest(BaseModel):
    actor: str


class VerifyRequest(BaseModel):
    cost_after: float


@router.get("")
def get_savings_summary():
    """Get savings summary: potential, approved, implemented, verified (realized)."""
    return savings_service.get_savings_summary()


@router.get("/audit-log")
def get_audit_log():
    """Get audit log of all recommendation lifecycle transitions."""
    log = savings_service.get_audit_log()
    return {"audit_log": log, "total": len(log)}


@router.get("/{recommendation_id}")
def get_recommendation_state(recommendation_id: str):
    """Get current lifecycle state of a recommendation."""
    result = savings_service.get_recommendation_state(recommendation_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Recommendation '{recommendation_id}' not found")
    return result


@router.post("/{recommendation_id}/approve")
def approve_recommendation(recommendation_id: str, body: ApproveRequest):
    """Approve a recommendation for implementation."""
    try:
        return savings_service.approve(recommendation_id, body.actor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{recommendation_id}/reject")
def reject_recommendation(recommendation_id: str, body: RejectRequest):
    """Reject a recommendation with reason."""
    try:
        return savings_service.reject(recommendation_id, body.actor, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{recommendation_id}/implement")
def implement_recommendation(recommendation_id: str, body: ImplementRequest):
    """Mark a recommendation as implemented."""
    try:
        return savings_service.implement(recommendation_id, body.actor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{recommendation_id}/verify")
def verify_recommendation(recommendation_id: str, body: VerifyRequest):
    """Verify savings with actual post-change cost data."""
    try:
        return savings_service.verify(recommendation_id, body.cost_after)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
