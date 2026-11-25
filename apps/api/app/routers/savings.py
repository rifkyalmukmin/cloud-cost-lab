from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.auth import require_principal
from app.services.savings_service import savings_service

router = APIRouter(prefix="/api/savings", tags=["savings"])


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Reason is required")
        if len(cleaned) > 500:
            raise ValueError("Reason must be 1-500 characters")
        return cleaned


class VerifyRequest(BaseModel):
    cost_after: float = Field(ge=0)

    @field_validator("cost_after")
    @classmethod
    def cost_after_is_finite(cls, value: float) -> float:
        if value != value or value == float("inf"):
            raise ValueError("cost_after must be a finite number >= 0")
        return value


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
def approve_recommendation(
    recommendation_id: str,
    principal: str = Depends(require_principal),
):
    """Approve a recommendation for implementation."""
    try:
        return savings_service.approve(recommendation_id, principal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{recommendation_id}/reject")
def reject_recommendation(
    recommendation_id: str,
    body: RejectRequest,
    principal: str = Depends(require_principal),
):
    """Reject a recommendation with reason."""
    try:
        return savings_service.reject(recommendation_id, principal, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{recommendation_id}/implement")
def implement_recommendation(
    recommendation_id: str,
    principal: str = Depends(require_principal),
):
    """Mark a recommendation as implemented."""
    try:
        return savings_service.implement(recommendation_id, principal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{recommendation_id}/verify")
def verify_recommendation(
    recommendation_id: str,
    body: VerifyRequest,
    _principal: str = Depends(require_principal),
):
    """Verify savings with actual post-change cost data."""
    try:
        return savings_service.verify(recommendation_id, body.cost_after)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
