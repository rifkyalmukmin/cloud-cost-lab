"""GCP Billing Export provider via BigQuery.

Queries GCP Billing Export tables with cost-safe patterns:
- Partition-aware queries (filter by _PARTITIONDATE)
- No SELECT *
- Bounded date ranges
- Column-specific selection
- Early aggregation

Requires:
- GCP_BILLING_PROJECT
- GCP_BILLING_DATASET
- GCP_BILLING_TABLE
- Authentication (service account key or Workload Identity Federation)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.providers.base import BillingDataProvider, DataFreshness

logger = logging.getLogger(__name__)


class GCPBillingProviderError(Exception):
    """Raised when GCP billing provider encounters an error."""
    pass


class GCPBillingProvider(BillingDataProvider):
    """Provider that reads from GCP Billing Export via BigQuery.

    All queries follow cost-safe patterns:
    1. _PARTITIONDATE filter (mandatory)
    2. Specific columns only (never SELECT *)
    3. Bounded date ranges (max 90 days)
    4. LIMIT clauses where appropriate
    """

    MAX_QUERY_DAYS = 90

    def __init__(
        self,
        project: str,
        dataset: str,
        table: str,
    ):
        self.project = project
        self.dataset = dataset
        self.table = table
        self._client = None

    @property
    def table_ref(self) -> str:
        return f"`{self.project}.{self.dataset}.{self.table}`"

    def _get_client(self):
        """Lazily initialize BigQuery client."""
        if self._client is not None:
            return self._client

        try:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.project)
            return self._client
        except ImportError:
            raise GCPBillingProviderError(
                "google-cloud-bigquery not installed. "
                "Install with: pip install google-cloud-bigquery"
            )
        except Exception as e:
            raise GCPBillingProviderError(
                f"Failed to initialize BigQuery client: {e}"
            )

    def get_cost_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Fetch cost records from BigQuery Billing Export.

        Uses partition-aware, column-specific query.
        Maximum range: 90 days.
        """
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=29))

        days_range = (end - start).days
        if days_range > self.MAX_QUERY_DAYS:
            start = end - timedelta(days=self.MAX_QUERY_DAYS)
            logger.warning(
                "Date range exceeded %d days, capping to %s",
                self.MAX_QUERY_DAYS, start.isoformat(),
            )

        query = f"""
        SELECT
            project.id AS project_id,
            project.name AS project_name,
            service.id AS service_id,
            service.description AS service_name,
            sku.id AS sku,
            location.region AS region,
            IFNULL(resource.name, '') AS resource_id,
            DATE(usage_start_time) AS usage_date,
            usage.amount AS usage_amount,
            usage.unit AS usage_unit,
            cost,
            currency,
            IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0) AS credits,
            cost + IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0) AS net_cost,
            IFNULL((SELECT l.value FROM UNNEST(labels) l WHERE l.key = 'environment'), '') AS environment,
            IFNULL((SELECT l.value FROM UNNEST(labels) l WHERE l.key = 'team'), '') AS team,
            IFNULL((SELECT l.value FROM UNNEST(labels) l WHERE l.key = 'application'), '') AS application
        FROM {self.table_ref}
        WHERE _PARTITIONDATE >= @start_date
          AND _PARTITIONDATE <= @end_date
        ORDER BY usage_date, service_name
        """

        try:
            from google.cloud import bigquery

            client = self._get_client()
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("start_date", "DATE", start.isoformat()),
                    bigquery.ScalarQueryParameter("end_date", "DATE", end.isoformat()),
                ]
            )

            result = client.query(query, job_config=job_config)
            records = []
            for row in result:
                records.append({
                    "project_id": row.project_id or "",
                    "project_name": row.project_name or "",
                    "service_id": row.service_id or "",
                    "service_name": row.service_name or "",
                    "sku": row.sku or "",
                    "region": row.region or "",
                    "resource_id": row.resource_id or "",
                    "usage_date": row.usage_date,
                    "usage_amount": float(row.usage_amount or 0),
                    "usage_unit": row.usage_unit or "",
                    "cost": float(row.cost or 0),
                    "currency": row.currency or "USD",
                    "credits": float(row.credits or 0),
                    "net_cost": float(row.net_cost or 0),
                    "environment": row.environment or "UNALLOCATED",
                    "team": row.team or "UNALLOCATED",
                    "application": row.application or "UNALLOCATED",
                })

            logger.info(
                "Fetched %d cost records from BigQuery (%s to %s)",
                len(records), start.isoformat(), end.isoformat(),
            )
            return records

        except GCPBillingProviderError:
            raise
        except Exception as e:
            raise GCPBillingProviderError(f"BigQuery query failed: {e}")

    def get_data_freshness(self) -> DataFreshness:
        """Check the latest partition date to determine data freshness."""
        query = f"""
        SELECT MAX(_PARTITIONDATE) AS latest_partition
        FROM {self.table_ref}
        WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        """

        try:
            client = self._get_client()
            result = client.query(query)
            row = next(iter(result), None)

            if row is None or row.latest_partition is None:
                return DataFreshness(status="UNKNOWN")

            latest = datetime.combine(row.latest_partition, datetime.min.time())
            now = datetime.utcnow()
            age_hours = (now - latest).total_seconds() / 3600

            if age_hours <= 36:
                status = "FRESH"
            else:
                status = "STALE"

            return DataFreshness(last_updated=latest, status=status)

        except Exception as e:
            logger.error("Failed to check data freshness: %s", e)
            return DataFreshness(status="UNKNOWN")

    def is_available(self) -> bool:
        """Check if BigQuery is accessible."""
        try:
            self._get_client()
            return True
        except GCPBillingProviderError:
            return False
