"""API response models for the utilization endpoints (Phase 4).

Phase 4 is an EVIDENCE layer: it shows how utilized each resource is and how
that relates to cost. It deliberately does not produce recommendations — the
recommendation engine consumes this evidence in a later phase.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from costlab.schemas.common import Environment
from costlab.schemas.cost import PaginationOut, PeriodOut
from costlab.schemas.resources import UtilizationPoint


class UtilizationFilters(BaseModel):
    """Shared utilization query filters — parsed once in `api.deps`."""

    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None
    project_id: str | None = None
    service: str | None = None  # services.id slug, e.g. "compute-engine"
    environment: Environment | None = None

    @model_validator(mode="after")
    def _check_range(self) -> UtilizationFilters:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class MetricStats(BaseModel):
    """Aggregate stats for ONE metric over the window.

    Computed in SQL over non-null samples only: a metric observed as 0% is a
    real zero and is kept; a metric with no samples at all is MISSING and is
    reported through `missing_metrics`, never as 0.
    """

    avg: float
    min: float
    max: float
    p95: float
    stddev: float | None  # null when fewer than 2 samples
    sample_count: int


class EvidenceSignals(BaseModel):
    """Project-specific heuristic evidence flags — not recommendations.

    Computed from CPU utilization when available; null when the resource has
    no CPU samples in the window (e.g. storage buckets), so "no signal" is
    distinguishable from "signal evaluated to false".
    """

    low_utilization: bool | None = None
    high_utilization: bool | None = None
    unstable_utilization: bool | None = None


class SignalCounts(BaseModel):
    """How many resources in the FULL filtered set carry each signal."""

    low_utilization: int
    high_utilization: int
    unstable_utilization: int
    missing_cpu: int


class UtilizationItem(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    service_name: str
    project_id: str
    project_name: str
    environment: Environment
    region: str

    window: PeriodOut
    metrics: dict[str, MetricStats]  # keyed by metric name, only metrics WITH samples
    missing_metrics: list[str]  # metrics with zero samples in the window
    avg_cpu: float | None  # convenience for charts/sorting; null when CPU missing

    cost_in_window: float | None  # gross cost over the SAME window as the stats
    cost_credits_in_window: float | None
    cost_net_in_window: float | None

    signals: EvidenceSignals


class UtilizationListResponse(BaseModel):
    window: PeriodOut | None
    pagination: PaginationOut
    signal_counts: SignalCounts
    items: list[UtilizationItem]


class UtilizationDetailResponse(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    service_name: str
    project_id: str
    project_name: str
    environment: Environment
    region: str
    machine_type: str | None = Field(default=None)

    window: PeriodOut
    metrics: dict[str, MetricStats]
    missing_metrics: list[str]
    cost_in_window: float | None
    cost_credits_in_window: float | None
    cost_net_in_window: float | None
    signals: EvidenceSignals
    series: list[UtilizationPoint]  # daily samples within the window, date ascending
