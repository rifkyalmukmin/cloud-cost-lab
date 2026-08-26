"""Monitoring provider factory — selects provider based on configuration."""

from app.config import settings
from app.providers.monitoring_base import MonitoringDataProvider
from app.providers.mock_monitoring import MockMonitoringProvider


def create_monitoring_provider() -> MonitoringDataProvider:
    """Create the appropriate monitoring provider based on DEMO_MODE.

    When DEMO_MODE=true (default): uses MockMonitoringProvider
    When DEMO_MODE=false: uses GCPMonitoringProvider (requires GCP config)
    """
    if settings.demo_mode:
        return MockMonitoringProvider()

    from app.providers.gcp_monitoring import GCPMonitoringProvider

    project = settings.gcp_billing_project
    if not project:
        raise RuntimeError(
            "GCP monitoring integration requires GCP_BILLING_PROJECT. "
            "Set DEMO_MODE=true to use mock data instead."
        )

    return GCPMonitoringProvider(project_id=project)
