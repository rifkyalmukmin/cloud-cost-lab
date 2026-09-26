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


class MonitoringDataProvider(ABC):
    """Per-resource monitoring/utilization samples (Phase 9, CLAUDE.md §10)."""

    name: str

    @abstractmethod
    def load_usage(self) -> list[UsageRecordInput]:
        """Load per-resource utilization samples."""


# Backward-compatible aliases (the monitoring interface subsumes usage).
UsageDataProvider = MonitoringDataProvider


class EmptyMonitoringProvider(MonitoringDataProvider):
    """Contributes no samples when monitoring is not configured. Utilization
    surfaces stay honest (missing data) — mock numbers are never mixed with
    real billing."""

    name = "none"

    def load_usage(self) -> list[UsageRecordInput]:
        return []


EmptyUsageProvider = EmptyMonitoringProvider
