"""AI Cloud Cost Advisor (Phase 14, CLAUDE.md §33-§35, ADR-008).

READ-ONLY by construction: the advisor analyses the platform's own
structured context and produces answers — it has no tools, no execution
capability and cannot touch cloud resources, IAM, firewalls or Terraform.
"""

from typing import Any

from costlab.ai.base import (
    UNSUPPORTED_QUESTION,
    AdvisorAnswer,
    AdvisorContext,
    AIAdvisorProvider,
)
from costlab.ai.context import build_advisor_context
from costlab.ai.mock import MockAdvisorProvider


def build_ai_provider(settings: Any) -> AIAdvisorProvider:
    """Pluggable advisor selection: deterministic mock by default; an
    OpenAI-compatible HTTP provider only when explicitly configured with
    AI_PROVIDER + AI_API_KEY (key from the environment, never committed)."""
    if settings.ai_provider == "mock" or not settings.ai_api_key:
        return MockAdvisorProvider()
    if settings.ai_provider == "openai-compatible":
        from costlab.ai.llm import LLMAPIProvider

        return LLMAPIProvider(settings)
    raise ValueError(f"Unknown AI_PROVIDER: {settings.ai_provider!r}")


__all__ = [
    "AIAdvisorProvider",
    "AdvisorAnswer",
    "AdvisorContext",
    "MockAdvisorProvider",
    "UNSUPPORTED_QUESTION",
    "build_advisor_context",
    "build_ai_provider",
]
