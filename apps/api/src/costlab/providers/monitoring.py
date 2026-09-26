"""GCP Cloud Monitoring provider (Phase 9, CLAUDE.md §10, §40).

Collects the available per-resource daily metrics and maps them onto the same
`UsageRecordInput` contract the mock provider satisfies:

- CPU        compute.googleapis.com/instance/cpu/utilization   (0-1 -> %)
- Memory     agent.googleapis.com/memory/percent_used          (ops agent)
- Disk       agent.googleapis.com/disk/percent_used            (ops agent)
- Network    instance/network/received_bytes_count + sent_bytes_count
- Connections (Cloud SQL) cloudsql.googleapis.com/database/.../connections
- Requests   loadbalancer.googleapis.com/https/request_count

Guarantees (mirroring the billing provider, all test-asserted):
- the monitoring client + query window are injected/bounded — no credentials
  in code (ADC locally, WIF in deployment);
- failures wrap into `GCPMonitoringError` with actionable messages;
- MISSING metrics (no series) stay `None` — never fabricated zeros;
- ZERO metrics (real observed zeros) are kept;
- STALE series (newest sample older than `GCP_MONITORING_MAX_AGE_DAYS`) are
  dropped with a log line instead of being ingested as fresh facts;
- the collection window is bounded by `GCP_MONITORING_MAX_DAYS` and ends
  yesterday (the running day is incomplete).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from costlab.providers.base import MonitoringDataProvider
from costlab.schemas.input import UsageRecordInput

logger = logging.getLogger("costlab.gcp-monitoring")


class GCPMonitoringError(RuntimeError):
    """Raised for Cloud Monitoring query/auth failures."""


@dataclass(frozen=True)
class MetricQuery:
    """One metric the provider knows how to ask Cloud Monitoring for."""

    key: str  # UsageRecordInput field name
    metric_type: str
    unit_scale: float = 1.0  # multiplied into samples (e.g. 0-1 -> percent)
    reducer: str = "MEAN"


# CPU unit in Monitoring is 0..1 utilization — scale to percent like the
# utilization model. The ops-agent metrics are already percent-valued.
METRIC_QUERIES: dict[str, MetricQuery] = {
    "cpu_utilization": MetricQuery(
        "cpu_utilization", "compute.googleapis.com/instance/cpu/utilization", unit_scale=100.0
    ),
    "memory_utilization": MetricQuery(
        "memory_utilization", "agent.googleapis.com/memory/percent_used"
    ),
    "disk_utilization": MetricQuery("disk_utilization", "agent.googleapis.com/disk/percent_used"),
    "network_in_mb": MetricQuery(
        "network_in_mb", "compute.googleapis.com/instance/network/received_bytes_count"
    ),
    "network_out_mb": MetricQuery(
        "network_out_mb", "compute.googleapis.com/instance/network/sent_bytes_count"
    ),
    "connections": MetricQuery(
        "connections", "cloudsql.googleapis.com/database/mysql/connections", reducer="MEAN"
    ),
    "request_count": MetricQuery(
        "request_count", "loadbalancer.googleapis.com/https/request_count", reducer="SUM"
    ),
}

# Network counters are cumulative bytes — converted to daily MB via deltas
# is approximated here with MEAN-scaled sums; documented limitation.
NETWORK_SCALE_TO_MB = 1.0 / (1024 * 1024)


def _default_query_runner(
    settings: Any,
) -> Callable[[MetricQuery, date, date], dict[str, dict[date, float]]]:
    """Production runner over Cloud Monitoring (lazy import, ADC/WIF)."""

    def runner(metric: MetricQuery, start: date, end: date) -> dict[str, dict[date, float]]:
        try:
            from google.cloud import monitoring_v3  # optional dependency (lazy)
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise GCPMonitoringError(
                "google-cloud-monitoring is not installed. Install the 'gcp' extra "
                "(pip install -e '.[gcp]') or run with DEMO_MODE=true."
            ) from exc
        try:
            client = monitoring_v3.MetricServiceClient()
            project_name = f"projects/{settings.gcp_monitoring_project}"
            interval = monitoring_v3.TimeInterval(
                {
                    "start_time": {
                        "seconds": int(datetime.combine(start, datetime.min.time()).timestamp())
                    },
                    "end_time": {
                        "seconds": int(
                            datetime.combine(
                                end + timedelta(days=1), datetime.min.time()
                            ).timestamp()
                        )
                    },
                }
            )
            aggregation = monitoring_v3.Aggregation(
                {
                    "alignment_period": {"seconds": 86400},
                    "per_series_aligner": getattr(
                        monitoring_v3.Aggregation.Aligner, f"ALIGN_{metric.reducer}"
                    ),
                }
            )
            request = monitoring_v3.ListTimeSeriesRequest(
                name=project_name,
                filter=f'metric.type = "{metric.metric_type}"',
                interval=interval,
                aggregation=aggregation,
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            )
            results: dict[str, dict[date, float]] = {}
            for series in client.list_time_series(request=request):
                resource_id = series.resource.labels.get(
                    "instance_id"
                ) or series.resource.labels.get("database_id")
                if not resource_id:
                    continue
                samples: dict[date, float] = {}
                for point in series.points:
                    day = point.interval.end_time.date()
                    value = point.value.double_value or point.value.int64_value or 0.0
                    samples[day] = value
                results[resource_id] = samples
            return results
        except GCPMonitoringError:
            raise
        except Exception as exc:
            raise GCPMonitoringError(
                f"Cloud Monitoring query failed for {metric.metric_type} "
                f"({type(exc).__name__}): {exc}. Check the API, permissions "
                "(roles/monitoring.viewer) and project settings."
            ) from exc

    return runner


class GCPMonitoringProvider(MonitoringDataProvider):
    """MonitoringDataProvider backed by Cloud Monitoring time series."""

    name = "gcp-monitoring"

    def __init__(
        self,
        settings: Any,
        query_runner: Callable[[MetricQuery, date, date], dict[str, dict[date, float]]]
        | None = None,
    ) -> None:
        self.project = settings.gcp_monitoring_project
        self.max_days = settings.gcp_monitoring_max_days
        self.max_age_days = settings.gcp_monitoring_max_age_days
        # Dependency injection: tests stub the runner; production uses the
        # Cloud Monitoring API via ADC / WIF — never key files.
        self._runner = query_runner or _default_query_runner(settings)

    def load_usage(self) -> list[UsageRecordInput]:
        end = datetime.now(UTC).date() - timedelta(days=1)
        start = end - timedelta(days=self.max_days - 1)

        # metric key -> resource id -> {date: value}
        collected: dict[str, dict[str, dict[date, float]]] = {}
        for metric in METRIC_QUERIES.values():
            try:
                collected[metric.key] = self._runner(metric, start, end)
            except GCPMonitoringError:
                raise
            except Exception as exc:
                raise GCPMonitoringError(
                    f"Cloud Monitoring query failed for {metric.key} "
                    f"({type(exc).__name__}): {exc}"
                ) from exc

        # Merge per (resource, day); metrics with no series stay None.
        merged: dict[tuple[str, date], dict[str, float | None]] = defaultdict(
            lambda: dict.fromkeys(METRIC_QUERIES)
        )
        last_sample: dict[str, date] = {}
        metric_by_key = {metric.key: metric for metric in METRIC_QUERIES.values()}
        for key, per_resource in collected.items():
            metric = metric_by_key[key]
            for resource_id, samples in per_resource.items():
                for day, raw in samples.items():
                    value = raw * metric.unit_scale
                    if metric.key.startswith("network"):
                        value *= NETWORK_SCALE_TO_MB  # cumulative bytes -> daily MB
                    merged[(resource_id, day)][key] = value
                    if resource_id not in last_sample or day > last_sample[resource_id]:
                        last_sample[resource_id] = day

        # Stale series are dropped entirely: ingesting old samples as if they
        # were current would misstate utilization (SRE honesty rule).
        dropped_stale = 0
        stale_cutoff = datetime.now(UTC).date() - timedelta(days=self.max_age_days)
        usable = {
            (resource_id, day): values
            for (resource_id, day), values in merged.items()
            if last_sample.get(resource_id, date.min) >= stale_cutoff
        }
        dropped_stale = len(merged) - len(usable)
        if dropped_stale:
            logger.warning(
                "dropped stale monitoring series",
                extra={"details": {"series": dropped_stale, "max_age_days": self.max_age_days}},
            )

        records = [
            UsageRecordInput(
                resource_id=resource_id,
                usage_date=day,
                cpu_utilization=values["cpu_utilization"],
                memory_utilization=values["memory_utilization"],
                disk_utilization=values["disk_utilization"],
                network_in_mb=values["network_in_mb"],
                network_out_mb=values["network_out_mb"],
                connections=int(values["connections"])
                if values["connections"] is not None
                else None,
                request_count=int(values["request_count"])
                if values["request_count"] is not None
                else None,
            )
            for (resource_id, day), values in sorted(usable.items())
        ]
        logger.info(
            "mapped monitoring samples",
            extra={"details": {"records": len(records), "series": len(last_sample)}},
        )
        return records
