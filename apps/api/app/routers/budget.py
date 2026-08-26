from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.services.budget_service import budget_service

router = APIRouter(prefix="/api/budget", tags=["budget"])


@router.get("")
def get_budget_status(
    reference_date: Optional[date] = Query(None, description="Reference date for budget calculation"),
):
    """Get current budget status with spending, utilization, and alerts."""
    return budget_service.get_budget_status(reference_date)
