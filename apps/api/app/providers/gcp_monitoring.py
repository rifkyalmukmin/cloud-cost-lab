"""GCP Cloud Monitoring provider.

Queries GCP Cloud Monitoring (Stackdriver) for resource metrics.
Uses the monitoring_v3 client library.

Requires:
- GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT
- Authentication (service account key or Workload Identity Federation)
- roles/monitoring.viewer permission
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.providers.monitoring_base import MetricsFreshness, MonitoringDataProvider

logger = logging.getLogger(__name__)


class GCPMonitoringProviderError(Exception):
    """Raised when GCP monitoring provider encounters an error."""
    pass


class GCPMonitoringProvider(MonitoringDataProvider):
    """Provider that reads from GCP Cloud Monitoring.

    Fetches compute.googleapis.com/instance/cpu/utilization,
    memory, disk, and network metrics.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            from google.cloud import monitoring_v3
            self._client = monitoring_v3.MetricServiceClient()
            return self._client
        except ImportError:
            raise GCPMonitoringProviderError(
                "google-cloud-monitoring not installed. "
                "Install with: pip install google-cloud-monitoring"
            )
        except Exception as e:
            raise GCPMonitoringProviderError(
                f"Failed to initialize monitoring client: {e}"
            )

    def get_resource_metrics(
        self,
        resource_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[dict]:
        """Fetch metrics from Cloud Monitoring for a resource."""
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=29))

        try:
            from google.cloud import monitoring_v3
            from google.protobuf.timestamp_pb2 import Timestamp

            client = self._get_client()
            project_name = f"projects/{self.project_id}"

            start_ts = Timestamp()
            start_ts.FromDatetime(datetime.combine(start, datetime.min.time()))
            end_ts = Timestamp()
            end_ts.FromDatetime(datetime.combine(end, datetime.max.time()))

            interval = monitoring_v3.TimeInterval(
                start_time=start_ts,
                end_time=end_ts,
            )

            cpu_series = self._query_metric(
                client, project_name, resource_id,
                "compute.googleapis.com/instance/cpu/utilization",
                interval,
            )

            return {
                "resource_id": resource_id,
                "cpu_utilization": cpu_series,
                "memory_utilization": None,
                "disk_utilization": None,
                "network_in_bytes": None,
                "network_out_bytes": None,
                "connections": None,
                "request_count": None,
                "latency_ms": None,
                "observation_days": (end - start).days + 1,
            }

        except GCPMonitoringProviderError:
            raise
        except Exception as e:
            logger.error("Failed to fetch metrics for %s: %s", resource_id, e)
            return None

    def _query_metric(self, client, project_name, resource_id, metric_type, interval):
        """Query a single metric from Cloud Monitoring."""
        try:
            from google.cloud import monitoring_v3

            results = client.list_time_series(
                request={
                    "name": project_name,
                    "filter": f'metric.type="{metric_type}" AND resource.labels.instance_id="{resource_id}"',
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                },
            )

            series = []
            for ts in results:
                for point in ts.points:
                    series.append({
                        "date": point.interval.end_time.isoformat()[:10],
                        "value": round(point.value.double_value * 100, 2),
                    })

            return series if series else None

        except Exception as e:
            logger.warning("Metric query failed for %s: %s", metric_type, e)
            return None

    def get_all_resource_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Fetch summary metrics for all resources.

        Note: This is expensive for many resources. Consider caching.
        """
        logger.warning("get_all_resource_metrics not fully implemented for GCP provider")
        return []

    def get_data_freshness(self) -> MetricsFreshness:
        """Cloud Monitoring data is near-real-time."""
        try:
            self._get_client()
            return MetricsFreshness(
                last_updated=datetime.utcnow(),
                status="FRESH",
            )
        except GCPMonitoringProviderError:
            return MetricsFreshness(status="UNKNOWN")

    def is_available(self) -> bool:
        try:
            self._get_client()
            return True
        except GCPMonitoringProviderError:
            return False
