"""API response models for the recommendation endpoints (Phase 5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from costlab.schemas.cost import PaginationOut, PeriodOut

RECOMMENDATION_STATUSES = ("OPEN", "APPROVED", "REJECTED", "IMPLEMENTED", "VERIFIED")
# IMPLEMENTED/VERIFIED transitions arrive with the savings-tracking phase;
# this phase opens the lifecycle and supports approve/reject decisions.
TRANSITIONABLE_STATUSES = ("OPEN",)
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
PRIORITY_LEVELS = ("HIGH", "MEDIUM", "LOW")


class EvidenceItem(BaseModel):
    statement: str
    metric: str | None = None
    value: float | None = None
    threshold: float | None = None
    unit: str | None = None


class VerificationResponse(BaseModel):
    id: str
    status: str
    realized_savings: float | None
    source: str  # "data" | "reported"
    before_daily_avg: float | None
    after_daily_avg: float | None
    before_days: int
    after_days: int


class ImplementBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    implemented_at: datetime | None = None  # backfill for verification exercises


class VerifyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_cost_after: float | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=256)


class RecommendationItem(BaseModel):
    id: str
    rule_id: str
    title: str
    resource_id: str | None
    resource_label: str
    project_id: str | None
    service_id: str | None

    problem: str
    evidence: list[EvidenceItem]
    recommendation: str

    current_cost: float
    potential_cost: float
    potential_savings: float
    savings_percentage: float

    risk: str
    confidence: str
    effort: str
    priority_score: float
    priority: str
    approval_required: bool
    status: str
    implemented_at: datetime | None
    verified_at: datetime | None
    actual_cost_after: float | None
    realized_savings: float | None

    window: PeriodOut | None
    created_at: datetime
    updated_at: datetime


class RecommendationSummary(BaseModel):
    by_status: dict[str, int]
    open_potential_savings: float


class RecommendationListResponse(BaseModel):
    summary: RecommendationSummary
    pagination: PaginationOut
    items: list[RecommendationItem]


class RunResponse(BaseModel):
    generated: int
    status_preserved: int
    removed: int


class TransitionResponse(BaseModel):
    id: str
    status: str


class StatusSavings(BaseModel):
    count: int
    potential_savings: float


class SavingsSummaryResponse(BaseModel):
    """Potential vs realized (CLAUDE.md §23) — realized only ever comes from
    VERIFIED rows with actual before/after measurement."""

    potential_savings: float
    approved_savings: float
    implemented: StatusSavings
    verified: StatusSavings
    realized_savings: float
    rejected_savings_foregone: float
    by_status: dict[str, StatusSavings]


class AuditLogOut(BaseModel):
    timestamp: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, object]
    request_id: str | None


class AuditLogListResponse(BaseModel):
    pagination: PaginationOut
    items: list[AuditLogOut]
