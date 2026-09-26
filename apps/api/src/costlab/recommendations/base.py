"""RecommendationRule interface and draft/value types (CLAUDE.md §22).

Each rule answers, for the evidence it observed:
- evaluate()      — inspect the data, return drafts (empty when no evidence);
- explain()       — WHY this recommendation exists, in plain language;
- calculate_saving() — money estimate derived ONLY from observed evidence;
- calculate_risk()   — what could go wrong if the action is taken;
- confidence()    — how much the data supports the claim.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

Risk = str  # LOW | MEDIUM | HIGH
Confidence = str  # HIGH | MEDIUM | LOW
Effort = str  # LOW | MEDIUM | HIGH


@dataclass(frozen=True)
class Evidence:
    """One observed fact backing a recommendation.

    `statement` is the human-readable sentence; `metric`, `value` and
    `threshold` keep the raw numbers so the UI and tests can re-check them.
    """

    statement: str
    metric: str | None = None
    value: float | None = None
    threshold: float | None = None
    unit: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"statement": self.statement}
        for key in ("metric", "value", "threshold", "unit"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload


@dataclass
class RecommendationDraft:
    """A rule's candidate recommendation, pre-priority.

    `suppressed_by` lists rule_ids whose draft on the SAME resource supersedes
    this one (e.g. an idle finding is the more specific action next to a
    generic oversized finding) — the engine drops superseded drafts.
    """

    rule_id: str
    title: str
    resource_id: str | None
    resource_label: str
    project_id: str | None
    service_id: str | None
    scope_key: str
    problem: str
    evidence: list[Evidence] = field(default_factory=list)
    recommendation: str = ""
    current_cost: float = 0.0
    potential_cost: float = 0.0
    potential_savings: float = 0.0
    savings_percentage: float = 0.0
    risk: Risk = "MEDIUM"
    confidence: Confidence = "MEDIUM"
    effort: Effort = "MEDIUM"
    window_start: Any = None
    window_end: Any = None
    suppressed_by: list[str] = field(default_factory=list)

    def add_evidence(self, item: Evidence) -> None:
        self.evidence.append(item)


class RecommendationRule(ABC):
    """Contract every recommendation rule implements (CLAUDE.md §22)."""

    rule_id: str
    title: str

    @abstractmethod
    def evaluate(self, session: Session, context: Any) -> list[RecommendationDraft]:
        """Inspect the data and return evidence-backed drafts (may be empty)."""

    @abstractmethod
    def explain(self, evidence: list[Evidence]) -> str:
        """WHY: plain-language explanation built from the given evidence."""

    @abstractmethod
    def calculate_saving(self, evidence: list[Evidence]) -> tuple[float, float, float]:
        """Return (current_cost, potential_cost, potential_savings).

        Must be derived from the evidence values only — never invented.
        """

    @abstractmethod
    def calculate_risk(self, evidence: list[Evidence]) -> Risk:
        """What could go wrong if the recommended action is taken."""

    @abstractmethod
    def confidence(self, evidence: list[Evidence]) -> Confidence:
        """How strongly the observed data supports the claim."""

    def build_draft(
        self,
        evidence: list[Evidence],
        *,
        resource_id: str | None,
        resource_label: str,
        project_id: str | None,
        service_id: str | None,
        scope_key: str,
        problem: str,
        recommendation: str,
        window_start: Any = None,
        window_end: Any = None,
        effort: Effort = "MEDIUM",
        suppressed_by: list[str] | None = None,
    ) -> RecommendationDraft:
        """Assemble a draft using the rule's own saving/risk/confidence methods."""
        current_cost, potential_cost, savings = self.calculate_saving(evidence)
        percentage = round(savings / current_cost * 100, 1) if current_cost > 0 else 0.0
        return RecommendationDraft(
            rule_id=self.rule_id,
            title=self.title,
            resource_id=resource_id,
            resource_label=resource_label,
            project_id=project_id,
            service_id=service_id,
            scope_key=scope_key,
            problem=problem,
            evidence=evidence,
            recommendation=recommendation,
            current_cost=round(current_cost, 4),
            potential_cost=round(potential_cost, 4),
            potential_savings=round(savings, 4),
            savings_percentage=percentage,
            risk=self.calculate_risk(evidence),
            confidence=self.confidence(evidence),
            effort=effort,
            window_start=window_start,
            window_end=window_end,
            suppressed_by=suppressed_by or [],
        )


def money(value: float | Decimal | None) -> float:
    return round(float(value or 0), 4)
