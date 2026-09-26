"""Budget + policy endpoints (Phase 6).

GET  /api/budget     evaluated budgets (status derived from current spend)
POST /api/budget     create a budget (validated; a data-only operation)
GET  /api/policies   advisory policy evaluation (PASS/WARNING/VIOLATION)

None of these endpoints can modify cloud infrastructure — budgets and
policies are rows in this application's database and their outcomes are
warnings/recommendations/audit information only (CLAUDE.md §34, §38).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from costlab.analytics.budget import budget_window, evaluate_budget, list_budgets
from costlab.db.models import Budget
from costlab.db.session import get_session
from costlab.governance import evaluate_policies
from costlab.schemas.governance import (
    BudgetCreate,
    BudgetListResponse,
    BudgetOut,
    BudgetSummary,
    PolicyFindingOut,
    PolicyListResponse,
    PolicyOut,
    PolicySummary,
)

router_budget = APIRouter(prefix="/api/budget", tags=["budget"])
router_policies = APIRouter(prefix="/api/policies", tags=["policies"])

SessionDep = Depends(get_session)


def _to_out(evaluation: dict[str, Any]) -> BudgetOut:
    return BudgetOut(**evaluation)


@router_budget.get("", response_model=BudgetListResponse)
def get_budgets(session: OrmSession = SessionDep) -> BudgetListResponse:
    budgets = list_budgets(session)
    window = budget_window(session)
    by_status: dict[str, int] = {"HEALTHY": 0, "WARNING": 0, "CRITICAL": 0, "EXCEEDED": 0}
    forecast_risk = 0
    for budget in budgets:
        if budget["status"] in by_status:
            by_status[budget["status"]] += 1
        if budget["forecast_over_budget"]:
            forecast_risk += 1
    return BudgetListResponse(
        summary=BudgetSummary(
            evaluation_month=window.month_start.isoformat() if window else None,
            data_end=window.data_end.isoformat() if window else None,
            budget_count=len(budgets),
            by_status=by_status,
            forecast_over_budget_count=forecast_risk,
        ),
        budgets=[_to_out(budget) for budget in budgets],
    )


@router_budget.post("", response_model=BudgetOut, status_code=201)
def create_budget(body: BudgetCreate, session: OrmSession = SessionDep) -> BudgetOut:
    """Create a budget. Data-only operation: writes a row to this database."""
    budget = Budget(
        id=uuid4().hex,
        name=body.name,
        scope_type=body.scope_type,
        scope_value=body.scope_value if body.scope_type != "all" else None,
        period=body.period,
        limit_amount=body.limit,
        warning_threshold=body.warning_threshold,
        critical_threshold=body.critical_threshold,
    )
    session.add(budget)
    session.commit()
    return _to_out(evaluate_budget(session, budget))


@router_policies.get("", response_model=PolicyListResponse)
def get_policies(session: OrmSession = SessionDep) -> PolicyListResponse:
    results = evaluate_policies(session)
    by_status: dict[str, int] = {"PASS": 0, "WARNING": 0, "VIOLATION": 0}
    finding_count = 0
    policies: list[PolicyOut] = []
    for result in results:
        by_status[result.status] += 1
        finding_count += len(result.findings)
        policies.append(
            PolicyOut(
                policy_id=result.policy_id,
                name=result.name,
                description=result.description,
                enabled=result.enabled,
                config=result.config,
                status=result.status,  # type: ignore[arg-type]  # evaluator contract
                summary=result.summary,
                findings=[
                    PolicyFindingOut(
                        resource_id=finding.resource_id,
                        resource_name=finding.resource_name,
                        detail=finding.detail,
                    )
                    for finding in result.findings
                ],
            )
        )
    return PolicyListResponse(
        summary=PolicySummary(
            policy_count=len(policies),
            by_status=by_status,
            finding_count=finding_count,
        ),
        policies=policies,
    )
