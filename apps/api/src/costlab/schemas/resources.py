"""API response models for the resource inventory endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from costlab.schemas.common import Environment
from costlab.schemas.cost import PaginationOut

# Potential savings require the Phase 4 recommendation engine. Until then the
# field exists in the contract but is always null — never guessed.
PotentialSaving = Literal[None]


class ResourceFilters(BaseModel):
    """Shared resource query filters — parsed once in `api.deps`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str | None = None
    service: str | None = None
    region: str | None = None
    environment: Environment | None = None
    status: str | None = None
    owner: str | None = None
    team: str | None = None
    # FinOps helper: only resources missing owner or team attribution.
    unallocated: bool = False


class ResourceWindow(BaseModel):
    """Trailing window used for monthly cost aggregation (data-anchored)."""

    start: date
    end: date


class ResourceCostSummary(BaseModel):
    monthly_cost: float
    monthly_credits: float
    monthly_net_cost: float


class ResourceItem(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    service_name: str
    project_id: str
    project_name: str
    region: str
    zone: str | None
    status: str
    environment: Environment
    machine_type: str | None
    owner: str | None
    team: str | None
    application: str | None
    labels: dict[str, str]
    created_at: datetime | None
    last_seen: datetime | None

    monthly_cost: float | None
    monthly_credits: float | None
    monthly_net_cost: float | None
    cpu_utilization: float | None
    memory_utilization: float | None
    potential_saving: PotentialSaving = None


class ResourceListResponse(BaseModel):
    window: ResourceWindow | None
    pagination: PaginationOut
    summary: ResourceCostSummary | None
    items: list[ResourceItem]


class CostHistoryPoint(BaseModel):
    date: date
    cost: float
    credits: float
    net_cost: float


class UtilizationPoint(BaseModel):
    date: date
    cpu_utilization: float | None
    memory_utilization: float | None
    disk_utilization: float | None
    network_in_mb: float | None
    network_out_mb: float | None
    request_count: int | None
    error_rate_pct: float | None


class ResourceDetailResponse(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    service_name: str
    project_id: str
    project_name: str
    region: str
    zone: str | None
    status: str
    environment: Environment
    machine_type: str | None
    owner: str | None
    team: str | None
    application: str | None
    labels: dict[str, str]
    created_at: datetime | None
    last_seen: datetime | None

    window: ResourceWindow | None
    monthly_cost: float | None
    monthly_credits: float | None
    monthly_net_cost: float | None
    total_cost: float | None
    total_net_cost: float | None
    cpu_utilization: float | None
    memory_utilization: float | None
    cost_history: list[CostHistoryPoint]
    utilization: list[UtilizationPoint]
    potential_saving: PotentialSaving = None
