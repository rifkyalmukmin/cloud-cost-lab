"""API response models for the cost endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from costlab.schemas.common import Environment, Granularity


class CostFilters(BaseModel):
    """Shared cost query filters — parsed once in `api.deps`, used by every
    `/api/cost` route and the analytics layer."""

    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None
    project_id: str | None = None
    service: str | None = None  # services.id slug, e.g. "compute-engine"
    environment: Environment | None = None
    region: str | None = None
    resource_id: str | None = None

    @model_validator(mode="after")
    def _check_range(self) -> CostFilters:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class PeriodOut(BaseModel):
    start: date
    end: date


class CostSummaryOut(BaseModel):
    cost: float
    credits: float
    net_cost: float


class CostRecordOut(BaseModel):
    usage_date: date
    project_id: str
    service: str
    service_name: str
    resource_id: str | None
    sku: str
    region: str
    environment: Environment
    usage_amount: float
    usage_unit: str
    cost: float
    credits: float
    net_cost: float
    currency: str
    labels: dict[str, str]


class PaginationOut(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class CostRecordsResponse(BaseModel):
    period: PeriodOut
    pagination: PaginationOut
    summary: CostSummaryOut
    items: list[CostRecordOut]


class TrendPointOut(BaseModel):
    period: date  # first day of the bucket (week buckets start on Monday)
    cost: float
    credits: float
    net_cost: float


class TrendResponse(BaseModel):
    period: PeriodOut
    granularity: Granularity
    points: list[TrendPointOut]


class ServiceBreakdownRowOut(BaseModel):
    service: str
    service_name: str
    cost: float
    credits: float
    net_cost: float
    share_pct: float


class ServiceBreakdownResponse(BaseModel):
    period: PeriodOut
    total: CostSummaryOut
    rows: list[ServiceBreakdownRowOut]


class ProjectBreakdownRowOut(BaseModel):
    project_id: str
    project_name: str
    cost: float
    credits: float
    net_cost: float
    share_pct: float


class ProjectBreakdownResponse(BaseModel):
    period: PeriodOut
    total: CostSummaryOut
    rows: list[ProjectBreakdownRowOut]


class EnvironmentBreakdownRowOut(BaseModel):
    environment: Environment
    cost: float
    credits: float
    net_cost: float
    share_pct: float


class EnvironmentBreakdownResponse(BaseModel):
    period: PeriodOut
    total: CostSummaryOut
    rows: list[EnvironmentBreakdownRowOut]


class HealthOut(BaseModel):
    status: str
    service: str
    version: str
    demo_mode: bool


class ReadyOut(BaseModel):
    status: str
    database: str
