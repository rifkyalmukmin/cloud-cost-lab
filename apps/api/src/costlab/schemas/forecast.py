"""API models for the forecast and anomaly endpoints (Phase 7)."""

from __future__ import annotations

from pydantic import BaseModel

from costlab.schemas.cost import PaginationOut


class ForecastMethodMovingAverage(BaseModel):
    window_days: int
    level: float


class ForecastMethodLinearTrend(BaseModel):
    fit_days: int
    slope_per_day: float
    r_squared: float


class ForecastHistory(BaseModel):
    start: str
    end: str
    daily_average: float


class ForecastPointOut(BaseModel):
    date: str
    moving_average: float
    linear_trend: float
    expected: float
    lower_bound: float
    upper_bound: float


class ForecastTotals(BaseModel):
    expected_30d: float
    lower_bound_30d: float
    upper_bound_30d: float


class ForecastResponse(BaseModel):
    sufficient_data: bool
    message: str | None = None
    history_days: int
    horizon_days: int
    history: ForecastHistory | None = None
    methods: dict[str, object] | None = None
    trend: str | None = None
    interval: str | None = None
    confidence: str | None = None
    forecast: list[ForecastPointOut]
    totals: ForecastTotals | None = None


class AnomalyItem(BaseModel):
    date: str
    project_id: str
    project_name: str
    service_id: str
    service_name: str
    resource_id: str | None
    resource_name: str | None
    actual: float
    expected: float
    difference: float
    percentage_change: float
    z_score: float | None
    severity: str
    confidence: str
    baseline_samples: int


class AnomalySummary(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_service: dict[str, int]


class AnomalyListResponse(BaseModel):
    summary: AnomalySummary
    pagination: PaginationOut
    items: list[AnomalyItem]
