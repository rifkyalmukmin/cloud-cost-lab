"""API response models for the recommendation endpoints (Phase 5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

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
