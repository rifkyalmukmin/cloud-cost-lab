"""Provider selection — the only place that knows which mode is active."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from costlab.config import Settings
from costlab.providers.base import (
    BillingDataProvider,
    EmptyUsageProvider,
    UsageDataProvider,
)
from costlab.providers.gcp import GCPBillingError as GCPBillingError
from costlab.providers.gcp import GCPBillingProvider
from costlab.providers.mock import MockBillingProvider, MockUsageProvider


@dataclass(frozen=True)
class ProviderSet:
    billing: BillingDataProvider
    usage: UsageDataProvider


def build_providers(settings: Settings) -> ProviderSet:
    """DEMO_MODE=true (the default) selects the mock providers. Real mode
    requires the GCP_BILLING_* settings and reads the BigQuery billing export;
    utilization still contributes no samples (no monitoring integration yet)."""
    if settings.demo_mode:
        data_dir = Path(settings.mock_data_dir)
        return ProviderSet(billing=MockBillingProvider(data_dir), usage=MockUsageProvider(data_dir))
    gcp_configured = (
        settings.gcp_billing_project and settings.gcp_billing_dataset and settings.gcp_billing_table
    )
    if not gcp_configured:
        raise RuntimeError(
            "DEMO_MODE=false requires GCP_BILLING_PROJECT, GCP_BILLING_DATASET and "
            "GCP_BILLING_TABLE (docs/gcp-setup.md), or set DEMO_MODE=true for the mock."
        )
    return ProviderSet(
        billing=GCPBillingProvider(settings),
        usage=EmptyUsageProvider(),
    )
