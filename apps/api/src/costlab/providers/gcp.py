"""GCP Billing Export provider (Phase 8, CLAUDE.md §8-§9).

Reads the standard BigQuery billing export table and maps it onto the same
`BillingSnapshot` contract the mock provider satisfies — nothing above the
providers knows which mode is active.

BigQuery cost protection (§9, verified by tests):
- the query filters `_PARTITIONTIME` (partition-aware) and `usage_start_time`;
- an explicit column whitelist — never `SELECT *`;
- date range bounded by `GCP_BILLING_MAX_DAYS`;
- a hard `LIMIT` row cap;
- a dry run first, logging the bytes that would be scanned;
- query parameters (no string interpolation of any value).

Security: no credentials are read from code or files by this module. The
BigQuery client is supplied by a factory (Application Default Credentials or
Workload Identity Federation in deployment); this module never touches key
files. Failures surface as `GCPBillingError` with actionable messages.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast

from costlab.providers.base import BillingDataProvider
from costlab.schemas.common import Environment
from costlab.schemas.input import (
    BillingSnapshot,
    CostRecordInput,
    ProjectInput,
    ResourceInput,
    ServiceInput,
)

logger = logging.getLogger("costlab.gcp")

# BigQuery billing export standard schema — explicit column whitelist.
QUERY_TEMPLATE = """
SELECT
  DATE(usage_start_time) AS usage_date,
  project.id AS project_id,
  project.name AS project_name,
  service.description AS service_name,
  sku.description AS sku_description,
  resource.global_name AS resource_id,
  resource.name AS resource_name,
  location.region AS region,
  labels,
  cost,
  (SELECT IFNULL(SUM(c.amount), 0) FROM UNNEST(credits) AS c) AS credits,
  usage.amount AS usage_amount,
  usage.unit AS usage_unit,
  currency,
  billing_account_id
FROM `{project}.{dataset}.{table}`
WHERE _PARTITIONTIME >= TIMESTAMP(@range_start)
  AND _PARTITIONTIME < TIMESTAMP(@range_end)
  AND usage_start_time >= TIMESTAMP(@range_start)
  AND usage_start_time < TIMESTAMP(@range_end)
GROUP BY
  usage_date, project_id, project_name, service_name, sku_description,
  resource_id, resource_name, region, labels, cost, credits,
  usage_amount, usage_unit, currency, billing_account_id
LIMIT @max_rows
"""

ENVIRONMENT_VALUES = ("development", "staging", "production")


class GCPBillingError(RuntimeError):
    """Raised for BigQuery/auth/malformed-data failures in the GCP provider."""


def _slugify(value: str) -> str:
    """'Compute Engine' -> 'compute-engine' (service id slug)."""
    return value.strip().lower().replace(" ", "-").replace("_", "-")


def _environment_from_labels(labels: dict[str, str]) -> Environment:
    """Environment attribution strictly from the `environment` label — never
    guessed (CLAUDE.md §12)."""
    value = labels.get("environment", "")
    if value in ENVIRONMENT_VALUES:
        return cast(Environment, value)
    return "UNALLOCATED"


def _labels_to_dict(raw: Any) -> dict[str, str]:
    """Export `labels` arrive as ARRAY<STRUCT<key, value>> (list of dicts)."""
    if not raw:
        return {}
    result: dict[str, str] = {}
    for item in raw:
        try:
            result[str(item["key"])] = str(item["value"])
        except (KeyError, TypeError, ValueError):
            continue  # a malformed label pair is dropped, not fatal
    return result


def _range(provider: GCPBillingProvider) -> tuple[date, date]:
    """Inclusive date range, capped at max_days, ending at the last complete
    UTC day (billing data for the running day is not yet final)."""
    end = datetime.now(UTC).date() - timedelta(days=1)
    start = end - timedelta(days=provider.max_days - 1)
    return start, end


class GCPBillingProvider(BillingDataProvider):
    """BillingDataProvider backed by the BigQuery billing export table."""

    name = "gcp-bigquery"

    def __init__(
        self,
        settings: Any,
        client_factory: Callable[[], Any] | None = None,
        job_configs_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.project = settings.gcp_billing_project
        self.dataset = settings.gcp_billing_dataset
        self.table = settings.gcp_billing_table
        self.location = settings.gcp_billing_location
        self.max_days = settings.gcp_billing_max_days
        self.max_rows = settings.gcp_billing_max_rows
        # Dependency injection: tests pass stub factories; production uses
        # Application Default Credentials / WIF (never key files from code).
        self._client_factory = client_factory or self._default_client_factory
        self._job_configs_factory = job_configs_factory or self._default_job_configs_factory

    def _default_client_factory(self) -> Any:
        try:
            from google.cloud import bigquery  # optional dependency (lazy import)
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise GCPBillingError(
                "google-cloud-bigquery is not installed. Install the 'gcp' extra "
                "(pip install -e '.[gcp]') or run with DEMO_MODE=true."
            ) from exc
        return bigquery.Client(project=self.project, location=self.location)

    def _default_job_configs_factory(self) -> Any:
        try:
            from google.cloud import bigquery  # optional dependency (lazy import)
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise GCPBillingError(
                "google-cloud-bigquery is not installed. Install the 'gcp' extra "
                "(pip install -e '.[gcp]') or run with DEMO_MODE=true."
            ) from exc

        class _Configs:
            def new_dry_run(self) -> Any:
                return bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)

            def with_parameters(self, parameters: list[tuple[str, str, Any]]) -> Any:
                return bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter(name, kind, value)
                        for name, kind, value in parameters
                    ]
                )

        return _Configs()

    # -- BigQuery access --------------------------------------------------

    def _query(self) -> tuple[str, list[tuple[str, Any, Any]]]:
        start, end = _range(self)
        parameters: list[tuple[str, Any, Any]] = [
            ("range_start", "TIMESTAMP", datetime.combine(start, datetime.min.time(), tzinfo=UTC)),
            (
                "range_end",
                "TIMESTAMP",
                datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
            ),
            ("max_rows", "INT64", self.max_rows),
        ]
        return (
            QUERY_TEMPLATE.format(project=self.project, dataset=self.dataset, table=self.table),
            parameters,
        )

    def _run_query(self) -> list[Any]:
        sql, parameters = self._query()
        try:
            client = self._client_factory()
        except GCPBillingError:
            raise
        except Exception as exc:
            raise GCPBillingError(
                f"Could not authenticate to BigQuery ({type(exc).__name__}: {exc}). "
                "Run `gcloud auth application-default login` locally, or configure "
                "Workload Identity Federation in deployment — never key files."
            ) from exc

        # Dry run first: log the bytes this query would scan (§9 cost guard).
        try:
            configs = self._job_configs_factory()
            dry_config = configs.new_dry_run()
            dry_job = client.query(sql, job_config=dry_config)
            logger.info(
                "bigquery dry run: %.2f MiB would be scanned",
                (dry_job.total_bytes_processed or 0) / (1024 * 1024),
                extra={"operation": "bq_dry_run"},
            )
            job_config = configs.with_parameters(parameters)
            result = client.query(sql, job_config=job_config).result()
        except GCPBillingError:
            raise
        except Exception as exc:
            raise GCPBillingError(
                f"BigQuery query failed ({type(exc).__name__}): {exc}. Check the export "
                "table name, location and permissions (docs/gcp-setup.md)."
            ) from exc

        return list(result)

    # -- Mapping -----------------------------------------------------------

    def load_snapshot(self) -> BillingSnapshot:
        rows = self._run_query()
        return self._map_rows(rows)

    def _map_rows(self, rows: list[Any]) -> BillingSnapshot:
        services: dict[str, ServiceInput] = {}
        projects: dict[str, ProjectInput] = {}
        resources: dict[str, ResourceInput] = {}
        cost_records: list[CostRecordInput] = []

        for row in rows:
            try:
                labels = _labels_to_dict(row["labels"])
                environment = _environment_from_labels(labels)
                service_name = str(row["service_name"])
                service_id = _slugify(service_name)
                project_id = str(row["project_id"])
                resource_id = row["resource_id"] or None

                services.setdefault(
                    service_id,
                    ServiceInput(
                        service_id=service_id,
                        display_name=service_name,
                        category="gcp",
                    ),
                )
                projects.setdefault(
                    project_id,
                    ProjectInput(
                        project_id=project_id,
                        display_name=str(row["project_name"] or project_id),
                        environment=environment,
                        labels={},
                    ),
                )
                if resource_id:
                    resources.setdefault(
                        str(resource_id),
                        ResourceInput(
                            resource_id=str(resource_id),
                            resource_name=str(row["resource_name"] or resource_id),
                            # The export schema does not carry a resource type
                            # column; a coarse classification beats a guess.
                            type="gcp_resource",
                            service_id=service_id,
                            project_id=project_id,
                            region=str(row["region"] or "global"),
                            status="ACTIVE",
                            environment=environment,
                            owner=labels.get("owner"),
                            team=labels.get("team"),
                            application=labels.get("application"),
                            labels=labels,
                            last_seen=None,
                        ),
                    )
                else:
                    # Unattributed billing line: an honest per-scope bucket
                    # resource, so cost is visible without pretending to know
                    # which resource it belongs to.
                    resource_id = f"unattributed:{project_id}:{service_id}"
                    resources.setdefault(
                        resource_id,
                        ResourceInput(
                            resource_id=resource_id,
                            resource_name=f"Unattributed — {service_name} ({project_id})",
                            type="unattributed",
                            service_id=service_id,
                            project_id=project_id,
                            region="global",
                            status="UNATTRIBUTED",
                            environment=environment,
                            labels=labels,
                        ),
                    )

                cost = float(row["cost"] or 0.0)
                credits = float(row["credits"] or 0.0)
                cost_records.append(
                    CostRecordInput(
                        resource_id=resource_id,
                        project_id=project_id,
                        service_id=service_id,
                        sku=str(row["sku_description"] or "unknown"),
                        region=str(row["region"] or "global"),
                        usage_date=row["usage_date"],
                        usage_amount=float(row["usage_amount"] or 0.0),
                        usage_unit=str(row["usage_unit"] or "unknown"),
                        cost=cost,
                        credits=credits,
                        net_cost=cost - credits,
                        currency=str(row["currency"] or "USD"),
                        environment=environment,
                        labels=labels,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                # Malformed export row: fail at the boundary with a clear
                # message instead of writing half-validated facts.
                raise GCPBillingError(
                    f"Malformed billing export row (missing/invalid field: {exc}). "
                    "Verify the export schema matches the standard billing export."
                ) from exc

        logger.info(
            "mapped billing snapshot",
            extra={
                "details": {
                    "services": len(services),
                    "projects": len(projects),
                    "resources": len(resources),
                    "cost_records": len(cost_records),
                }
            },
        )
        return BillingSnapshot(
            source=f"bigquery:{self.project}.{self.dataset}.{self.table}",
            services=sorted(services.values(), key=lambda s: s.service_id),
            projects=sorted(projects.values(), key=lambda p: p.project_id),
            resources=sorted(resources.values(), key=lambda r: r.resource_id),
            cost_records=cost_records,
        )
