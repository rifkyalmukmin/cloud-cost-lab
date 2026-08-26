from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class CostSummary(BaseModel):
    current_month_cost: float
    previous_month_cost: float
    mom_change_percent: float
    average_daily_cost: float
    projected_month_cost: float
    potential_savings: float
    currency: str = "USD"
    data_freshness: datetime


class CostByDimension(BaseModel):
    dimension: str
    value: str
    total_cost: float
    net_cost: float
    percentage: float


class DailyCost(BaseModel):
    date: date
    cost: float
    net_cost: float


class CostTrendResponse(BaseModel):
    daily_costs: list[DailyCost]
    period_start: date
    period_end: date
    total_cost: float


class CostBreakdownResponse(BaseModel):
    breakdown: list[CostByDimension]
    total_cost: float
    period_start: date
    period_end: date


class CostQueryParams(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    service: Optional[str] = None
    project: Optional[str] = None
    environment: Optional[str] = None
    region: Optional[str] = None


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    data: list
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    demo_mode: bool


class ReadyResponse(BaseModel):
    status: str
    database: str
    data_loaded: bool
