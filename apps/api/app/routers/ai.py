from datetime import date
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.ai.advisor import cost_advisor

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)


@router.post("/ask")
def ask_advisor(body: AskRequest, reference_date: Optional[date] = Query(None)):
    """Ask the AI Cloud Cost Advisor a question.

    The advisor is READ-ONLY — it analyzes data and provides recommendations
    but cannot modify any infrastructure.
    """
    return cost_advisor.analyze(body.question, reference_date)


@router.get("/capabilities")
def get_capabilities():
    """List AI advisor capabilities and safety constraints."""
    return {
        "name": "AI Cloud Cost Advisor",
        "mode": "READ-ONLY",
        "capabilities": [
            "Analyze cost trends and explain increases",
            "Identify savings opportunities",
            "Find idle or underutilized resources",
            "Explain cost anomalies",
            "Summarize cost forecasts",
            "Prioritize optimization recommendations",
            "Analyze budget status",
        ],
        "cannot_do": [
            "Delete resources",
            "Modify IAM policies",
            "Change firewall rules",
            "Destroy Terraform infrastructure",
            "Modify databases",
            "Execute any write operation on infrastructure",
        ],
        "safety": {
            "read_only": True,
            "prompt_injection_protection": True,
            "sensitive_data_filtering": True,
            "insufficient_evidence_handling": True,
        },
        "example_questions": [
            "Why did cost increase this month?",
            "Where can I save money?",
            "Which resource should I optimize first?",
            "What caused the cost anomaly?",
            "What is my cost forecast?",
            "Which recommendation has the highest priority?",
            "What is my budget status?",
        ],
    }
