from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.services.forecast_service import forecast_service

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("")
def get_cost_forecast(
    reference_date: Optional[date] = Query(None, description="Reference date (default: today)"),
    days_ahead: int = Query(30, ge=1, le=90, description="Days to forecast ahead"),
):
    """Get cost forecast with confidence range."""
    return forecast_service.forecast_cost(reference_date, days_ahead)
