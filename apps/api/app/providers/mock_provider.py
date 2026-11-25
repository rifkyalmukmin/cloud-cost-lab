"""Mock billing data provider.

Uses deterministic synthetic data. Works without GCP credentials.
Default provider when DEMO_MODE=true.
"""

from datetime import date, datetime
from typing import Optional

from app.providers.base import BillingDataProvider, DataFreshness
from app.services.mock_data import generate_cost_records


class MockBillingProvider(BillingDataProvider):
    """Provider that uses synthetic, deterministic billing data."""

    def get_cost_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        return generate_cost_records(start_date, end_date)

    def get_data_freshness(self) -> DataFreshness:
        return DataFreshness(
            last_updated=datetime(2026, 8, 26, 4, 0, 0),
            status="FRESH",
        )

    def is_available(self) -> bool:
        return True
