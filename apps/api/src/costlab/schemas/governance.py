"""API models for budget and policy endpoints (Phase 6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BudgetScopeType = Literal["all", "project", "service", "environment"]
BudgetStatus = Literal["HEALTHY", "WARNING", "CRITICAL", "EXCEEDED"]
PolicyStatus = Literal["PASS", "WARNING", "VIOLATION"]


class BudgetCreate(BaseModel):
    """POST /api/budget body — validated hard (Security mode)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    scope_type: BudgetScopeType = "all"
    scope_value: str | None = Field(default=None, max_length=64)
    period: Literal["monthly"] = "monthly"
    limit: float = Field(gt=0, le=1_000_000)
    warning_threshold: float = Field(gt=0, lt=100)
    critical_threshold: float = Field(gt=0, lt=100)

    @model_validator(mode="after")
    def _check_thresholds_and_scope(self) -> BudgetCreate:
        if self.warning_threshold >= self.critical_threshold:
            raise ValueError("warning_threshold must be strictly below critical_threshold")
        if self.scope_type != "all" and not self.scope_value:
            raise ValueError("scope_value is required unless scope_type is 'all'")
        return self


class SpendPeriod(BaseModel):
    start: str
    end: str
    days_elapsed: int
    days_in_month: int


class SpendOut(BaseModel):
    amount: float
    gross_amount: float
    daily_average: float
    period: SpendPeriod


class BudgetOut(BaseModel):
    id: str
    name: str
    scope_type: str
    scope_value: str | None
    period: str
    limit: float
    warning_threshold: float
    critical_threshold: float
    status: BudgetStatus | None
    spend: SpendOut | None
    remaining: float | None
    spend_percentage: float | None
    # Linear run-rate estimate — never presented as a guaranteed number (§15).
    projected_month_end: float | None
    forecast_over_budget: bool | None


class BudgetSummary(BaseModel):
    evaluation_month: str | None
    data_end: str | None
    budget_count: int
    by_status: dict[str, int]
    forecast_over_budget_count: int


class BudgetListResponse(BaseModel):
    summary: BudgetSummary
    budgets: list[BudgetOut]


class PolicyFindingOut(BaseModel):
    resource_id: str | None
    resource_name: str
    detail: str


class PolicyOut(BaseModel):
    policy_id: str
    name: str
    description: str
    enabled: bool
    config: dict[str, object]
    status: PolicyStatus
    summary: str
    findings: list[PolicyFindingOut]


class PolicySummary(BaseModel):
    policy_count: int
    by_status: dict[str, int]
    finding_count: int


class PolicyListResponse(BaseModel):
    summary: PolicySummary
    policies: list[PolicyOut]
