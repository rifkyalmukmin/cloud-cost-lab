from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.services.anomaly_service import anomaly_service

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.get("")
def detect_cost_anomalies(
    reference_date: Optional[date] = Query(None, description="Reference date (default: today)"),
    lookback_days: int = Query(30, ge=7, le=90, description="Days to analyze"),
):
    """Detect cost anomalies using z-score analysis."""
    return anomaly_service.detect_anomalies(reference_date, lookback_days)
