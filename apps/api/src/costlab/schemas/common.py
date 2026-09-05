"""Domain vocabulary shared by every layer."""

from __future__ import annotations

from typing import Literal

Environment = Literal["development", "staging", "production"]
ENVIRONMENTS: tuple[str, ...] = ("development", "staging", "production")
Granularity = Literal["day", "week", "month"]
GRANULARITIES: tuple[str, ...] = ("day", "week", "month")
