"""Provider selection — the only place that knows which mode is active."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from costlab.config import Settings
from costlab.providers.base import (
    BillingDataProvider,
    RealBillingProvider,
    RealUsageProvider,
    UsageDataProvider,
)
from costlab.providers.mock import MockBillingProvider, MockUsageProvider


@dataclass(frozen=True)
class ProviderSet:
    billing: BillingDataProvider
    usage: UsageDataProvider


def build_providers(settings: Settings) -> ProviderSet:
    """DEMO_MODE=true (the default) selects the mock providers; anything else
    selects the real GCP providers, which currently fail loudly (Phase 9)."""
    if settings.demo_mode:
        data_dir = Path(settings.mock_data_dir)
        return ProviderSet(billing=MockBillingProvider(data_dir), usage=MockUsageProvider(data_dir))
    return ProviderSet(billing=RealBillingProvider(), usage=RealUsageProvider())
