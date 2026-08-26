from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.utilization_service import utilization_service

router = APIRouter(prefix="/api/utilization", tags=["utilization"])


@router.get("")
def get_utilization_summary(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get utilization summary across all resources with pattern analysis."""
    return utilization_service.get_utilization_summary(start_date, end_date)


@router.get("/{resource_id}")
def get_resource_utilization(
    resource_id: str,
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get detailed utilization for a specific resource."""
    result = utilization_service.get_resource_utilization(resource_id, start_date, end_date)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Resource '{resource_id}' not found")
    return result


@router.get("/cost-vs-utilization/data")
def get_cost_vs_utilization(
    start_date: Optional[date] = Query(None, description="Start date (default: month start)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get cost vs utilization data for all resources."""
    return utilization_service.get_cost_vs_utilization(start_date, end_date)
