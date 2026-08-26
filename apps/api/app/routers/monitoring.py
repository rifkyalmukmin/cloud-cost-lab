from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.monitoring_service import monitoring_service

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("")
def get_enriched_metrics(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get enriched resource metrics with cost correlation and evidence strength."""
    return monitoring_service.get_enriched_resource_metrics(start_date, end_date)


@router.get("/{resource_id}")
def get_resource_metrics(
    resource_id: str,
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get detailed monitoring metrics for a specific resource."""
    result = monitoring_service.get_resource_detail_metrics(resource_id, start_date, end_date)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Resource '{resource_id}' not found")
    return result
