"""Base billing data provider interface.

All billing providers (mock, GCP) must implement this interface.
This enables seamless switching between demo mode and real GCP billing data.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional


class DataFreshness:
    """Tracks how fresh the billing data is."""

    def __init__(
        self,
        last_updated: Optional[datetime] = None,
        status: str = "UNKNOWN",
    ):
        self.last_updated = last_updated
        self.status = status

    @property
    def data_age_hours(self) -> Optional[float]:
        if self.last_updated is None:
            return None
        now = datetime(2026, 8, 26, 12, 0, 0)
        delta = now - self.last_updated
        return round(delta.total_seconds() / 3600, 1)

    def to_dict(self) -> dict:
        return {
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "data_age_hours": self.data_age_hours,
            "status": self.status,
        }


class BillingDataProvider(ABC):
    """Abstract base for all billing data providers."""

    @abstractmethod
    def get_cost_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Fetch cost records for the given date range.

        Returns:
            List of cost record dicts with fields:
                project_id, project_name, service_id, service_name,
                sku, region, resource_id, usage_date, usage_amount,
                usage_unit, cost, currency, credits, net_cost,
                environment, team, application
        """
        pass

    @abstractmethod
    def get_data_freshness(self) -> DataFreshness:
        """Check how fresh the billing data is.

        Returns:
            DataFreshness with last_updated timestamp and status (FRESH/STALE/UNKNOWN)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available.

        Returns:
            True if provider can serve data, False otherwise
        """
        pass
