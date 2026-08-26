from fastapi import APIRouter

from app.services.policy_service import policy_service

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("")
def evaluate_policies():
    """Evaluate all governance policies against all resources."""
    return policy_service.evaluate_policies()
