"""Recommendation engine: run all rules, prioritize, persist (CLAUDE.md §22-§24).

The run is observation/recommendation mode only (§38): it writes rows to this
application's database and NEVER touches cloud infrastructure. Re-runs upsert
by (rule_id, scope_key) and preserve the human-decided status of unchanged
recommendations; drafts that disappear are removed.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from costlab.analytics import utilization as utilization_analytics
from costlab.db.models import Recommendation
from costlab.recommendations.base import RecommendationDraft, RecommendationRule
from costlab.recommendations.rules import (
    CostAnomalyRule,
    IdleComputeRule,
    OversizedComputeRule,
    StorageRetentionRule,
    UnusedDiskRule,
)
from costlab.schemas.utilization import UtilizationFilters

# --- Project-specific priority model (CLAUDE.md §24) -------------------------
# score = 40*savings + 25*confidence + 20*risk-inverse + 15*effort-inverse
# where savings saturates at $10/month (lab-scale reference point). The
# result is a ranking heuristic for THIS project — not an industry standard.
PRIORITY_WEIGHTS = {
    "confidence": {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3},
    "risk": {"LOW": 1.0, "MEDIUM": 0.5, "HIGH": 0.0},
    "effort": {"LOW": 1.0, "MEDIUM": 0.5, "HIGH": 0.0},
}
SAVINGS_SATURATION_USD = 10.0
PRIORITY_HIGH_MIN = 70.0
PRIORITY_MEDIUM_MIN = 45.0


def priority_score(draft: RecommendationDraft) -> float:
    savings_component = min(1.0, max(0.0, draft.potential_savings) / SAVINGS_SATURATION_USD)
    score = (
        40 * savings_component
        + 25 * PRIORITY_WEIGHTS["confidence"][draft.confidence]
        + 20 * PRIORITY_WEIGHTS["risk"][draft.risk]
        + 15 * PRIORITY_WEIGHTS["effort"][draft.effort]
    )
    return round(score, 1)


def priority_label(score: float) -> str:
    if score >= PRIORITY_HIGH_MIN:
        return "HIGH"
    if score >= PRIORITY_MEDIUM_MIN:
        return "MEDIUM"
    return "LOW"


class EngineContext:
    """Everything rules may read: utilization stats + costs per resource."""

    def __init__(self, session: Session) -> None:
        rows: list[utilization_analytics.UtilizationRow] = []
        page = 1
        window = None
        # The aggregate is bounded by the resource dimension; page through it
        # so rules never silently see only the first page.
        while True:
            batch, pagination, _counts, window = utilization_analytics.list_utilization(
                session, UtilizationFilters(), page, page_size=100
            )
            rows.extend(batch)
            if page >= pagination.total_pages or not batch:
                break
            page += 1
        self.utilization_rows = rows
        self.window = window


def build_rules() -> list[RecommendationRule]:
    return [
        IdleComputeRule(),
        OversizedComputeRule(),
        UnusedDiskRule(),
        StorageRetentionRule(),
        CostAnomalyRule(),
    ]


def _collect_drafts(session: Session, context: EngineContext) -> list[RecommendationDraft]:
    drafts: list[RecommendationDraft] = []
    for rule in build_rules():
        drafts.extend(rule.evaluate(session, context))
    # Suppression: a more specific finding removes the generic one for the
    # same scope (e.g. idle supersedes oversized on the same VM).
    suppressed_keys = {(draft.rule_id, draft.scope_key) for draft in drafts if draft.suppressed_by}
    kept: list[RecommendationDraft] = []
    for draft in drafts:
        superseding = {
            (superior, draft.scope_key)
            for superior in draft.suppressed_by
            if any(
                other.rule_id == superior and other.scope_key == draft.scope_key for other in drafts
            )
        }
        if superseding & suppressed_keys or any(
            other.rule_id in draft.suppressed_by and other.scope_key == draft.scope_key
            for other in drafts
        ):
            continue
        kept.append(draft)
    return kept


def run_engine(session: Session) -> dict[str, int]:
    """Run every rule and persist the result. Returns run statistics."""
    context = EngineContext(session)
    drafts = _collect_drafts(session, context)

    drafts.sort(key=lambda d: (-priority_score(d), d.rule_id, d.scope_key))
    existing = {
        (row.rule_id, row.scope_key): row
        for row in session.execute(select(Recommendation)).scalars()
    }
    seen: set[tuple[str, str]] = set()
    stats = {"generated": 0, "status_preserved": 0, "removed": 0}

    for draft in drafts:
        key = (draft.rule_id, draft.scope_key)
        seen.add(key)
        row = existing.get(key)
        if row is None:
            row = Recommendation(id=uuid4().hex, rule_id=draft.rule_id, scope_key=draft.scope_key)
            session.add(row)
        else:
            stats["status_preserved"] += 1
        score = priority_score(draft)
        row.resource_id = draft.resource_id
        row.project_id = draft.project_id
        row.service_id = draft.service_id
        row.title = draft.title
        row.problem = draft.problem
        row.evidence = [item.as_dict() for item in draft.evidence]
        row.recommendation = draft.recommendation
        row.current_cost = Decimal(str(draft.current_cost))
        row.potential_cost = Decimal(str(draft.potential_cost))
        row.potential_savings = Decimal(str(draft.potential_savings))
        row.savings_percentage = Decimal(str(draft.savings_percentage))
        row.risk = draft.risk
        row.confidence = draft.confidence
        row.effort = draft.effort
        row.priority_score = Decimal(str(score))
        row.priority = priority_label(score)
        row.approval_required = True
        row.window_start = draft.window_start
        row.window_end = draft.window_end
        row.status = row.status or "OPEN"
        stats["generated"] += 1

    stale = [key for key in existing if key not in seen]
    for rule_id, scope_key in stale:
        session.execute(
            delete(Recommendation).where(
                Recommendation.rule_id == rule_id, Recommendation.scope_key == scope_key
            )
        )
    stats["removed"] = len(stale)
    return stats
