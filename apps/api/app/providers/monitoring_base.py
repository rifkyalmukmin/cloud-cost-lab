"""Base monitoring data provider interface.

All monitoring providers (mock, GCP) must implement this interface.
Monitoring data is used to correlate cost with utilization and performance.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional


class MetricsFreshness:
    """Tracks how fresh the monitoring metrics are."""

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


class MonitoringDataProvider(ABC):
    """Abstract base for all monitoring data providers."""

    @abstractmethod
    def get_resource_metrics(
        self,
        resource_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[dict]:
        """Fetch metrics for a specific resource.

        Returns:
            dict with available metrics or None if resource not found.
            Fields (all optional — None means metric unavailable):
                cpu_utilization: list of {date, value}
                memory_utilization: list of {date, value}
                disk_utilization: list of {date, value}
                network_in_bytes: list of {date, value}
                network_out_bytes: list of {date, value}
                connections: list of {date, value}
                request_count: list of {date, value}
                latency_ms: list of {date, value}
        """
        pass

    @abstractmethod
    def get_all_resource_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Fetch summary metrics for all known resources.

        Returns:
            list of dicts, each with:
                resource_id: str
                cpu_avg: float | None
                memory_avg: float | None
                disk_avg: float | None
                network_in_avg_mb: float | None
                network_out_avg_mb: float | None
                connections_avg: float | None
                request_count_daily_avg: float | None
                latency_avg_ms: float | None
                observation_days: int
        """
        pass

    @abstractmethod
    def get_data_freshness(self) -> MetricsFreshness:
        """Check how fresh the monitoring data is.

        Returns:
            MetricsFreshness with last_updated and status (FRESH/STALE/UNKNOWN)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and reachable."""
        pass
