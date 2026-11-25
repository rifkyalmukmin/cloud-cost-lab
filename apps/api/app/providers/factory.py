"""Provider factory — selects billing provider based on configuration."""

from app.config import settings
from app.providers.base import BillingDataProvider
from app.providers.mock_provider import MockBillingProvider


def create_billing_provider() -> BillingDataProvider:
    """Create the appropriate billing provider based on DEMO_MODE.

    When DEMO_MODE=true (default): uses MockBillingProvider
    When DEMO_MODE=false: uses GCPBillingProvider (requires GCP config)
    """
    if settings.demo_mode:
        return MockBillingProvider()

    from app.providers.gcp_provider import GCPBillingProvider

    project = settings.gcp_billing_project
    dataset = settings.gcp_billing_dataset
    table = settings.gcp_billing_table

    if project is None or dataset is None or table is None:
        raise RuntimeError(
            "GCP billing integration requires GCP_BILLING_PROJECT, "
            "GCP_BILLING_DATASET, and GCP_BILLING_TABLE environment variables. "
            "Set DEMO_MODE=true to use mock data instead."
        )

    return GCPBillingProvider(
        project=project,
        dataset=dataset,
        table=table,
    )
