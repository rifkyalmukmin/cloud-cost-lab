from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.services.cost_service import cost_service

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.get("")
def get_cost_summary(
    reference_date: Optional[date] = Query(None, description="Reference date for summary calculation"),
):
    """Get cost summary: current month, previous month, MoM change, projection."""
    return cost_service.get_summary(reference_date)


@router.get("/trend")
def get_cost_trend(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get daily cost trend for the given period."""
    return cost_service.get_trend(start_date, end_date)


@router.get("/by-service")
def get_cost_by_service(
    start_date: Optional[date] = Query(None, description="Start date (default: month start)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get cost breakdown by GCP service."""
    return cost_service.get_by_service(start_date, end_date)


@router.get("/by-project")
def get_cost_by_project(
    start_date: Optional[date] = Query(None, description="Start date (default: month start)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get cost breakdown by GCP project."""
    return cost_service.get_by_project(start_date, end_date)


@router.get("/by-environment")
def get_cost_by_environment(
    start_date: Optional[date] = Query(None, description="Start date (default: month start)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
):
    """Get cost breakdown by environment (production, staging, development)."""
    return cost_service.get_by_environment(start_date, end_date)
