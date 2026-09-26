"""Rule-based recommendation engine (Phase 5).

Architecture (CLAUDE.md §22-§24, §38):
- rules are pluggable classes implementing `RecommendationRule`;
- every recommendation carries WHY / EVIDENCE / SAVING / RISK / CONFIDENCE /
  EFFORT — nothing is asserted without observed data;
- the engine runs in observation/recommendation mode only: it writes rows to
  THIS application's database and never touches cloud infrastructure;
- every recommendation requires human approval before any action.
"""

from costlab.recommendations.base import (
    Evidence,
    RecommendationDraft,
    RecommendationRule,
)
from costlab.recommendations.engine import (
    build_rules,
    priority_label,
    priority_score,
    run_engine,
)
from costlab.recommendations.rules import (
    CostAnomalyRule,
    IdleComputeRule,
    OversizedComputeRule,
    StorageRetentionRule,
    UnusedDiskRule,
)

__all__ = [
    "CostAnomalyRule",
    "Evidence",
    "IdleComputeRule",
    "OversizedComputeRule",
    "RecommendationDraft",
    "RecommendationRule",
    "StorageRetentionRule",
    "UnusedDiskRule",
    "build_rules",
    "priority_label",
    "priority_score",
    "run_engine",
]
