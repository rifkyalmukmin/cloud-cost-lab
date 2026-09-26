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

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from costlab.analytics.savings import compute_realized_savings, savings_summary
from costlab.api.deps import SessionDep
from costlab.db.models import AuditLog, Recommendation, Resource
from costlab.governance.audit import record_audit
from costlab.recommendations.engine import run_engine
from costlab.schemas.cost import PaginationOut, PeriodOut
from costlab.schemas.recommendations import (
    PRIORITY_LEVELS,
    RECOMMENDATION_STATUSES,
    RISK_LEVELS,
    AuditLogListResponse,
    AuditLogOut,
    EvidenceItem,
    ImplementBody,
    RecommendationItem,
    RecommendationListResponse,
    RecommendationSummary,
    RunResponse,
    SavingsSummaryResponse,
    TransitionResponse,
    VerificationResponse,
    VerifyBody,
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
        implemented_at=row.implemented_at,
        verified_at=row.verified_at,
        actual_cost_after=(
            float(row.actual_cost_after) if row.actual_cost_after is not None else None
        ),
        realized_savings=(
            float(row.realized_savings) if row.realized_savings is not None else None
        ),
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


@router.get("/savings", response_model=SavingsSummaryResponse)
def get_savings(session: SessionDep) -> SavingsSummaryResponse:
    """Potential vs realized savings across the lifecycle (CLAUDE.md §23)."""
    return SavingsSummaryResponse(**savings_summary(session))


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    session: SessionDep,
    entity_id: Annotated[str | None, Query(max_length=64)] = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AuditLogListResponse:
    """Append-only audit trail, newest first (bounded)."""
    stmt = select(AuditLog)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    total = int(session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    rows = (
        session.execute(
            stmt.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return AuditLogListResponse(
        pagination=PaginationOut(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
        items=[
            AuditLogOut(
                timestamp=row.timestamp,
                actor=row.actor,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                details=row.details or {},
                request_id=row.request_id,
            )
            for row in rows
        ],
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


# Allowed source statuses per target (CLAUDE.md §23 lifecycle).
LIFECYCLE_SOURCES: dict[str, tuple[str, ...]] = {
    "APPROVED": ("OPEN",),
    "REJECTED": ("OPEN",),
    "IMPLEMENTED": ("APPROVED",),
    "VERIFIED": ("IMPLEMENTED",),
}


def _get_row_or_404(session: OrmSession, recommendation_id: str) -> Recommendation:
    row = session.get(Recommendation, recommendation_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Recommendation {recommendation_id!r} was not found."
        )
    return row


def _transition(
    session: OrmSession,
    recommendation_id: str,
    target: str,
    *,
    extra_details: dict[str, Any] | None = None,
) -> Recommendation:
    row = _get_row_or_404(session, recommendation_id)
    allowed = LIFECYCLE_SOURCES[target]
    if row.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Recommendation is {row.status}; only {'/'.join(allowed)} "
                f"recommendations can move to {target}."
            ),
        )
    previous_status = row.status
    row.status = target
    record_audit(
        session,
        action=target.lower(),
        entity_type="recommendation",
        entity_id=row.id,
        details={"from": previous_status, "to": target, **(extra_details or {})},
    )
    return row


@router.post("/{recommendation_id}/approve", response_model=TransitionResponse)
def approve(session: SessionDep, recommendation_id: str) -> TransitionResponse:
    """Human approval — the platform itself never takes the action."""
    row = _transition(session, recommendation_id, "APPROVED")
    session.commit()
    return TransitionResponse(id=row.id, status=row.status)


@router.post("/{recommendation_id}/reject", response_model=TransitionResponse)
def reject(session: SessionDep, recommendation_id: str) -> TransitionResponse:
    row = _transition(session, recommendation_id, "REJECTED")
    session.commit()
    return TransitionResponse(id=row.id, status=row.status)


@router.post("/{recommendation_id}/implement", response_model=TransitionResponse)
def implement(
    session: SessionDep,
    recommendation_id: str,
    body: ImplementBody | None = None,
) -> TransitionResponse:
    """APPROVED -> IMPLEMENTED: the human has performed the change themselves
    (or had it performed). The platform only records it. An optional
    `implemented_at` backfills the date for verification exercises."""
    row = _get_row_or_404(session, recommendation_id)
    implemented_at = body.implemented_at if body and body.implemented_at else datetime.now(UTC)
    row.implemented_at = implemented_at
    row = _transition(session, recommendation_id, "IMPLEMENTED")
    session.commit()
    return TransitionResponse(id=row.id, status=row.status)


@router.post("/{recommendation_id}/verify", response_model=VerificationResponse)
def verify(
    session: SessionDep,
    recommendation_id: str,
    body: VerifyBody | None = None,
) -> VerificationResponse:
    """IMPLEMENTED -> VERIFIED: compare actual before/after cost.

    The before/after windows come from real cost records when the data exists;
    otherwise a caller-measured `actual_cost_after` (monthly-equivalent) may be
    supplied. Without either, verification refuses — simulated savings are
    never called realized.
    """
    row = _get_row_or_404(session, recommendation_id)
    if row.status != "IMPLEMENTED":
        allowed = "/".join(LIFECYCLE_SOURCES["VERIFIED"])
        raise HTTPException(
            status_code=409,
            detail=(
                f"Recommendation is {row.status}; only {allowed} "
                "recommendations can be verified."
            ),
        )
    implemented_at = row.implemented_at or datetime.now(UTC)
    implemented_on = implemented_at.date()

    reported = body.actual_cost_after if body and body.actual_cost_after is not None else None
    result = compute_realized_savings(
        session, row.resource_id or "", implemented_on, reported_actual_cost_after=reported
    )
    if result.realized_savings is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot verify yet: no post-implementation cost data exists "
                f"(after days observed: {result.after_days}). Savings stay "
                "potential until actual after-data is available."
            ),
        )

    after_daily = result.after_daily_avg or 0.0
    row.verified_at = datetime.now(UTC)
    row.actual_cost_after = Decimal(str(round(after_daily * 30.0, 4)))
    row.realized_savings = Decimal(str(result.realized_savings))
    row.status = "VERIFIED"
    record_audit(
        session,
        action="verified",
        entity_type="recommendation",
        entity_id=row.id,
        details={
            "from": "IMPLEMENTED",
            "source": result.source,
            "before_daily_avg": result.before_daily_avg,
            "after_daily_avg": result.after_daily_avg,
            "before_days": result.before_days,
            "after_days": result.after_days,
            "realized_savings": result.realized_savings,
        },
    )
    session.commit()
    return VerificationResponse(
        id=row.id,
        status=row.status,
        realized_savings=result.realized_savings,
        source=result.source,
        before_daily_avg=result.before_daily_avg,
        after_daily_avg=result.after_daily_avg,
        before_days=result.before_days,
        after_days=result.after_days,
    )
