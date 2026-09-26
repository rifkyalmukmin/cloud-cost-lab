"""Domain vocabulary shared by every layer."""

from __future__ import annotations

from typing import Literal

# UNALLOCATED marks resources/cost rows whose environment cannot be
# determined from provider data (CLAUDE.md §12) — attribution is never guessed.
Environment = Literal["development", "staging", "production", "UNALLOCATED"]
ENVIRONMENTS: tuple[str, ...] = ("development", "staging", "production")
Granularity = Literal["day", "week", "month"]
GRANULARITIES: tuple[str, ...] = ("day", "week", "month")
