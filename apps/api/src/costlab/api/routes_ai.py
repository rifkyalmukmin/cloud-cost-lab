"""AI Cloud Cost Advisor endpoints (Phase 14).

POST /api/ai/advisor  ask a cost question; the advisor reasons over the
                      platform's structured context and returns the
                      seven-section answer (§35)
GET  /api/ai/status   which provider is active + the safety contract

READ-ONLY (CLAUDE.md §34): the advisor cannot delete resources, modify IAM,
change firewalls, destroy databases, run terraform destroy or modify
production — it has no tools and no execution path. Prompt-injection
attempts are refused.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from costlab.ai import build_advisor_context, build_ai_provider
from costlab.ai.base import (
    ANSWER_SECTIONS,
    SAFETY_STATEMENT,
    is_injection_attempt,
    sanitize_question,
)
from costlab.api.deps import SessionDep
from costlab.config import get_settings

router = APIRouter(prefix="/api/ai", tags=["ai"])

SUPPORTED_QUESTIONS = (
    "Why did cost increase?",
    "Where can I save?",
    "Which resource should I optimize?",
    "What caused the anomaly?",
    "What is my forecast?",
    "Which recommendation has highest priority?",
)


class AdvisorQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)


@router.get("/status")
def status() -> dict[str, Any]:
    settings = get_settings()
    provider = build_ai_provider(settings)
    return {
        "provider": provider.name,
        "read_only": True,
        "safety": SAFETY_STATEMENT,
        "supported_questions": list(SUPPORTED_QUESTIONS),
    }


@router.post("/advisor")
def advisor(body: AdvisorQuestion, session: SessionDep) -> dict[str, Any]:
    settings = get_settings()
    provider = build_ai_provider(settings)

    question = sanitize_question(body.question)
    if not question:
        raise HTTPException(status_code=422, detail="Question is empty after sanitization.")
    if is_injection_attempt(question):
        # Answer through the same refusal path as the deterministic provider:
        # never execute, never pretend the instruction was followed.
        provider_answer = provider.answer(question, build_advisor_context(session, settings))
        return provider_answer.as_dict()

    try:
        context = build_advisor_context(session, settings)
        provider_answer = provider.answer(question, context)
    except Exception as exc:  # noqa: BLE001  # advisory must fail with context, not crash
        raise HTTPException(
            status_code=502,
            detail=f"Advisor failed to produce an answer: {exc}",
        ) from exc

    answer = provider_answer.as_dict()
    answer["notes"].append(
        "Advisor output is generated from platform data — verify claims on the "
        "dashboard pages before acting. Sections: " + ", ".join(ANSWER_SECTIONS) + "."
    )
    return answer
