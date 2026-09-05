"""Data provider abstraction (ADR-003).

Mock and real GCP data sources implement the same interfaces; no layer above
the providers may know which mode is active. The real GCP integration lands in
Phase 9 (ADR-004) — until then `RealBillingProvider` fails loudly and clearly
instead of pretending to work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from costlab.schemas.input import BillingSnapshot, UsageRecordInput


class BillingDataProvider(ABC):
    name: str

    @abstractmethod
    def load_snapshot(self) -> BillingSnapshot:
        """Load services, projects, resources and cost records."""


class UsageDataProvider(ABC):
    name: str

    @abstractmethod
    def load_usage(self) -> list[UsageRecordInput]:
        """Load per-resource utilization samples."""


class RealBillingProvider(BillingDataProvider):
    name = "real-gcp"

    def load_snapshot(self) -> BillingSnapshot:
        raise NotImplementedError(
            "Real GCP billing integration is planned for Phase 9 (ADR-004). "
            "Run with DEMO_MODE=true to use the mock provider."
        )


class RealUsageProvider(UsageDataProvider):
    name = "real-gcp"

    def load_usage(self) -> list[UsageRecordInput]:
        raise NotImplementedError(
            "Real GCP monitoring integration is planned for Phase 9 (ADR-004). "
            "Run with DEMO_MODE=true to use the mock provider."
        )
