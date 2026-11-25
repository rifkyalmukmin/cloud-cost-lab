"""Frozen demo clock.

Billing, recommendations, and audit timestamps still use 26 August 2026.
The label is shown in the UI until that clock is replaced with the real date.
"""

from datetime import date

DEMO_AS_OF = date(2026, 8, 26)
SNAPSHOT_LABEL = "data demo per 26 Agu 2026"
