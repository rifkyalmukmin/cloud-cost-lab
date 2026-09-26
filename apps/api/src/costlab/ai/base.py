"""AI advisor contracts: answer shape, context envelope and the safety rules
every provider must honour (CLAUDE.md §34, ADR-008)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Every answer must carry these sections (CLAUDE.md §35).
ANSWER_SECTIONS = (
    "summary",
    "evidence",
    "likely_cause",
    "recommendation",
    "potential_savings",
    "risk",
    "confidence",
)

UNSUPPORTED_QUESTION = (
    "Insufficient evidence: this question is outside the advisor's scope. "
    "Supported questions: why did cost increase, where can I save, which "
    "resource should I optimize, what caused the anomaly, what is my "
    "forecast, which recommendation has highest priority."
)

# Untrusted question text is truncated and control characters are stripped
# before it reaches any provider (prompt-injection hygiene, §34).
QUESTION_MAX_CHARS = 500

FORBIDDEN_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all",
    "disregard",
    "forget your instructions",
    "delete ",
    "destroy ",
    "terraform apply",
    "terraform destroy",
    "drop table",
    "rm -rf",
)

SAFETY_STATEMENT = (
    "The advisor is read-only: it cannot delete resources, modify IAM, "
    "change firewalls, destroy databases, run terraform destroy or modify "
    "production. All actions require human approval via the recommendation "
    "lifecycle."
)


@dataclass
class AdvisorContext:
    """The structured, whitelisted facts an advisor may reason over."""

    environment: dict[str, Any]
    cost: dict[str, Any]
    resources: dict[str, Any]
    utilization: dict[str, Any]
    recommendations: dict[str, Any]
    anomalies: dict[str, Any]
    forecast: dict[str, Any]
    budget: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "cost": self.cost,
            "resources": self.resources,
            "utilization": self.utilization,
            "recommendations": self.recommendations,
            "anomalies": self.anomalies,
            "forecast": self.forecast,
            "budget": self.budget,
        }


@dataclass
class AdvisorAnswer:
    intent: str
    sections: dict[str, Any]  # the ANSWER_SECTIONS keys
    mode: str  # "mock" | provider name
    safety: str = SAFETY_STATEMENT
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "answer": self.sections,
            "mode": self.mode,
            "safety": self.safety,
            "notes": self.notes,
        }


class AIAdvisorProvider(ABC):
    """Pluggable advisor backend. READ-ONLY: implementations analyse the
    provided context and return text — they are never given tools, database
    write access or cloud credentials."""

    name: str

    @abstractmethod
    def answer(self, question: str, context: AdvisorContext) -> AdvisorAnswer:
        """Answer the question from the structured context only."""


def sanitize_question(raw: str | None) -> str:
    """Strip control characters and cap length (untrusted input hygiene)."""
    if not raw:
        return ""
    cleaned = "".join(ch for ch in raw if ch.isprintable())
    return cleaned.strip()[:QUESTION_MAX_CHARS]


def is_injection_attempt(question: str) -> bool:
    """Conservative marker check: instruction-override or action-imperative
    language in the question is treated as a prompt-injection attempt."""
    lowered = question.lower()
    return any(marker in lowered for marker in FORBIDDEN_INJECTION_MARKERS)
