"""Input contracts for data providers.

These models validate external data (the mock JSON files now; real GCP Billing
Export rows in Phase 9) before anything reaches the database.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from costlab.schemas.common import Environment

ServiceSlug = str  # services.id, e.g. "compute-engine"


class ServiceInput(BaseModel):
    service_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)


class ProjectInput(BaseModel):
    project_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    environment: Environment
    labels: dict[str, str] = Field(default_factory=dict)


class ResourceInput(BaseModel):
    resource_id: str = Field(min_length=1, max_length=128)
    resource_name: str = Field(min_length=1, max_length=256)
    type: str = Field(min_length=1, max_length=64)
    service_id: ServiceSlug
    project_id: str = Field(min_length=1, max_length=64)
    region: str = Field(min_length=1, max_length=64)
    zone: str | None = Field(default=None, max_length=64)
    status: str = Field(min_length=1, max_length=32)
    environment: Environment
    machine_type: str | None = Field(default=None, max_length=64)
    owner: str | None = Field(default=None, max_length=64)
    team: str | None = Field(default=None, max_length=64)
    application: str | None = Field(default=None, max_length=64)
    labels: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    last_seen: datetime | None = None


class CostRecordInput(BaseModel):
    resource_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=64)
    service_id: ServiceSlug
    sku: str = Field(min_length=1, max_length=256)
    region: str = Field(min_length=1, max_length=64)
    usage_date: date
    usage_amount: float = Field(ge=0)
    usage_unit: str = Field(min_length=1, max_length=32)
    cost: float = Field(ge=0)
    credits: float = Field(default=0.0, ge=0)
    net_cost: float
    currency: str = Field(min_length=3, max_length=3)
    environment: Environment
    labels: dict[str, str] = Field(default_factory=dict)


class UsageRecordInput(BaseModel):
    resource_id: str = Field(min_length=1, max_length=128)
    usage_date: date
    cpu_utilization: float | None = Field(default=None, ge=0, le=100)
    memory_utilization: float | None = Field(default=None, ge=0, le=100)
    disk_utilization: float | None = Field(default=None, ge=0, le=100)
    network_in_mb: float | None = Field(default=None, ge=0)
    network_out_mb: float | None = Field(default=None, ge=0)
    request_count: int | None = Field(default=None, ge=0)
    latency_ms: float | None = Field(default=None, ge=0)
    error_rate_pct: float | None = Field(default=None, ge=0, le=100)


class BillingSnapshot(BaseModel):
    """Everything a billing provider can contribute in one load."""

    source: str
    services: list[ServiceInput]
    projects: list[ProjectInput]
    resources: list[ResourceInput]
    cost_records: list[CostRecordInput]
