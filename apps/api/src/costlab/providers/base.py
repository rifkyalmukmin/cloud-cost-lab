"""Data provider abstraction (ADR-003).

Mock and real GCP data sources implement the same interfaces; no layer above
the providers may know which mode is active. The real billing side is the
BigQuery-backed `GCPBillingProvider` (Phase 8); real *utilization* (Cloud
Monitoring) is not integrated yet, so real mode contributes no usage samples
and the utilization layers report missing data honestly.
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


class EmptyUsageProvider(UsageDataProvider):
    """Real-mode usage source placeholder: contributes no samples until the
    Cloud Monitoring integration exists. Utilization surfaces stay honest
    (missing data), never mock numbers next to real billing."""

    name = "none"

    def load_usage(self) -> list[UsageRecordInput]:
        return []
