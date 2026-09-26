"""Recommendation endpoints (Phase 5).

GET  /api/recommendations            filtered, sorted, paginated list
GET  /api/recommendations/{id}       full detail (evidence, savings math)
POST /api/recommendations/run        re-run the rule engine (recommendation
                                     mode only — writes OUR database, never
                                     touches cloud infrastructure)
POST /api/recommendations/{id}/approve   OPEN -> APPROVED (human decision)
POST /api/recommendations/{id}/reject    OPEN -> REJECTED  (human decision)

IMPLEMENTED/VERIFIED transitions belong to the savings-tracking phase.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from costlab.api.deps import SessionDep
from costlab.db.models import Recommendation, Resource
from costlab.recommendations.engine import run_engine
from costlab.schemas.cost import PaginationOut, PeriodOut
from costlab.schemas.recommendations import (
    PRIORITY_LEVELS,
    RECOMMENDATION_STATUSES,
    RISK_LEVELS,
    TRANSITIONABLE_STATUSES,
    EvidenceItem,
    RecommendationItem,
    RecommendationListResponse,
    RecommendationSummary,
    RunResponse,
    TransitionResponse,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _label_for(resource_id: str | None, project_id: str | None, service_id: str | None) -> str:
    if resource_id:
        return resource_id
    parts = [p for p in (project_id, service_id) if p]
    return " / ".join(parts) if parts else "-"


def _item(row: Recommendation, resource_names: dict[str, str]) -> RecommendationItem:
    return RecommendationItem(
        id=row.id,
        rule_id=row.rule_id,
        title=row.title,
        resource_id=row.resource_id,
        resource_label=(
            resource_names.get(row.resource_id, row.resource_id)
            if row.resource_id
            else _label_for(None, row.project_id, row.service_id)
        ),
        project_id=row.project_id,
        service_id=row.service_id,
        problem=row.problem,
        evidence=[EvidenceItem(**item) for item in (row.evidence or [])],
        recommendation=row.recommendation,
        current_cost=float(row.current_cost),
        potential_cost=float(row.potential_cost),
        potential_savings=float(row.potential_savings),
        savings_percentage=float(row.savings_percentage),
        risk=row.risk,
        confidence=row.confidence,
        effort=row.effort,
        priority_score=float(row.priority_score),
        priority=row.priority,
        approval_required=row.approval_required,
        status=row.status,
        window=(
            PeriodOut(start=row.window_start, end=row.window_end)
            if row.window_start and row.window_end
            else None
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validate_sort(sort: str) -> None:
    if sort not in ("priority", "savings", "recent"):
        raise HTTPException(status_code=422, detail=f"Invalid sort: {sort!r}")


@router.get("", response_model=RecommendationListResponse)
def list_recommendations(
    session: SessionDep,
    status: Annotated[str | None, Query(description="OPEN | APPROVED | REJECTED | ...")] = None,
    rule_id: Annotated[str | None, Query(max_length=64, description="e.g. idle_compute")] = None,
    risk: Annotated[str | None, Query(description="LOW | MEDIUM | HIGH")] = None,
    priority: Annotated[str | None, Query(description="HIGH | MEDIUM | LOW")] = None,
    resource_id: Annotated[str | None, Query(max_length=128)] = None,
    project_id: Annotated[str | None, Query(max_length=64)] = None,
    sort: Annotated[str, Query(description="priority | savings | recent")] = "priority",
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> RecommendationListResponse:
    if status and status not in RECOMMENDATION_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {status!r}")
    if risk and risk not in RISK_LEVELS:
        raise HTTPException(status_code=422, detail=f"Invalid risk: {risk!r}")
    if priority and priority not in PRIORITY_LEVELS:
        raise HTTPException(status_code=422, detail=f"Invalid priority: {priority!r}")
    _validate_sort(sort)

    stmt = select(Recommendation)
    if status:
        stmt = stmt.where(Recommendation.status == status)
    if rule_id:
        stmt = stmt.where(Recommendation.rule_id == rule_id)
    if risk:
        stmt = stmt.where(Recommendation.risk == risk)
    if priority:
        stmt = stmt.where(Recommendation.priority == priority)
    if resource_id:
        stmt = stmt.where(Recommendation.resource_id == resource_id)
    if project_id:
        stmt = stmt.where(Recommendation.project_id == project_id)

    total = int(session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())

    order_by_clauses: list[Any]
    if sort == "savings":
        order_by_clauses = [Recommendation.potential_savings.desc(), Recommendation.rule_id.asc()]
    elif sort == "recent":
        order_by_clauses = [Recommendation.updated_at.desc(), Recommendation.rule_id.asc()]
    else:  # priority (default)
        order_by_clauses = [Recommendation.priority_score.desc(), Recommendation.rule_id.asc()]
    rows = (
        session.execute(
            stmt.order_by(*order_by_clauses).offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )

    status_counts: dict[str, int] = {
        row[0]: int(row[1])
        for row in session.execute(
            select(Recommendation.status, func.count()).group_by(Recommendation.status)
        ).all()
    }
    open_savings = session.execute(
        select(func.coalesce(func.sum(Recommendation.potential_savings), 0)).where(
            Recommendation.status.in_(("OPEN", "APPROVED"))
        )
    ).scalar_one()  # OPEN + APPROVED = savings awaiting implementation

    resource_names = {
        resource_id: name
        for resource_id, name in session.execute(
            select(Resource.resource_id, Resource.resource_name)
        ).all()
    }
    return RecommendationListResponse(
        summary=RecommendationSummary(
            by_status={s: int(status_counts.get(s, 0)) for s in RECOMMENDATION_STATUSES},
            open_potential_savings=round(float(open_savings), 4),
        ),
        pagination=PaginationOut(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
        items=[_item(row, resource_names) for row in rows],
    )


@router.get("/{recommendation_id}", response_model=RecommendationItem)
def get_recommendation(session: SessionDep, recommendation_id: str) -> RecommendationItem:
    row = session.get(Recommendation, recommendation_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Recommendation {recommendation_id!r} was not found."
        )
    resource_names = {
        resource_id: name
        for resource_id, name in session.execute(
            select(Resource.resource_id, Resource.resource_name)
        ).all()
    }
    return _item(row, resource_names)


@router.post("/run", response_model=RunResponse)
def run(session: SessionDep) -> RunResponse:
    """Re-run the rule engine over the current data.

    Recommendation mode only: creates/updates rows in this application's
    database. It does NOT modify any cloud resource (CLAUDE.md §38).
    """
    stats = run_engine(session)
    session.commit()
    return RunResponse(**stats)


def _transition(session: SessionDep, recommendation_id: str, target: str) -> TransitionResponse:
    row = session.get(Recommendation, recommendation_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Recommendation {recommendation_id!r} was not found."
        )
    if row.status not in TRANSITIONABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Recommendation is {row.status}; only "
                f"{'/'.join(TRANSITIONABLE_STATUSES)} recommendations can move to {target}."
            ),
        )
    row.status = target
    session.commit()
    return TransitionResponse(id=row.id, status=row.status)


@router.post("/{recommendation_id}/approve", response_model=TransitionResponse)
def approve(session: SessionDep, recommendation_id: str) -> TransitionResponse:
    """Human approval — the platform itself never takes the action."""
    return _transition(session, recommendation_id, "APPROVED")


@router.post("/{recommendation_id}/reject", response_model=TransitionResponse)
def reject(session: SessionDep, recommendation_id: str) -> TransitionResponse:
    return _transition(session, recommendation_id, "REJECTED")
