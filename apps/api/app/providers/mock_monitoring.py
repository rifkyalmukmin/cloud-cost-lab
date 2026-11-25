"""Mock monitoring data provider.

Uses deterministic synthetic data for CPU, memory, disk, network,
connections, requests, and latency. Works without GCP credentials.
"""

import hashlib
import random
from datetime import date, datetime, timedelta
from typing import Optional

from app.clock import reference_today
from app.providers.monitoring_base import MetricsFreshness, MonitoringDataProvider
from app.services.mock_data import RESOURCE_UTILIZATION, RESOURCES, SEED

# Extended metrics beyond basic utilization
RESOURCE_EXTENDED_METRICS: dict[str, dict] = {
    "vm-prod-api-01": {
        "connections_avg": 120.0,
        "request_count_daily_avg": 45000.0,
        "latency_avg_ms": 85.0,
    },
    "vm-prod-api-02": {
        "connections_avg": 95.0,
        "request_count_daily_avg": 38000.0,
        "latency_avg_ms": 92.0,
    },
    "vm-dev-01": {
        "connections_avg": 5.0,
        "request_count_daily_avg": 200.0,
        "latency_avg_ms": 120.0,
    },
    "vm-idle-01": {
        "connections_avg": 0.0,
        "request_count_daily_avg": 0.0,
        "latency_avg_ms": 0.0,
    },
    "sql-prod-01": {
        "connections_avg": 42.0,
        "request_count_daily_avg": 85000.0,
        "latency_avg_ms": 12.0,
    },
    "sql-staging-01": {
        "connections_avg": 8.0,
        "request_count_daily_avg": 3500.0,
        "latency_avg_ms": 18.0,
    },
    "gcs-prod-assets": {
        "connections_avg": None,
        "request_count_daily_avg": 12000.0,
        "latency_avg_ms": 45.0,
    },
    "ar-prod-images": {
        "connections_avg": None,
        "request_count_daily_avg": 150.0,
        "latency_avg_ms": 200.0,
    },
}


def _deterministic_metric(resource_id: str, metric: str, day: date, base: float) -> float:
    key = f"mon:{resource_id}:{metric}:{day.isoformat()}:{SEED}"
    hash_val = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    rng = random.Random(hash_val)
    variation = rng.uniform(0.7, 1.3)
    return round(base * variation, 2)


class MockMonitoringProvider(MonitoringDataProvider):
    """Provider that uses synthetic, deterministic monitoring metrics."""

    def get_resource_metrics(
        self,
        resource_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[dict]:
        resource = None
        for r in RESOURCES:
            if r["resource_id"] == resource_id:
                resource = r
                break
        if resource is None:
            return None

        end = end_date or reference_today()
        start = start_date or (end - timedelta(days=29))

        base_util = RESOURCE_UTILIZATION.get(resource_id, {})
        ext_metrics = RESOURCE_EXTENDED_METRICS.get(resource_id, {})

        cpu_series = []
        memory_series = []
        disk_series = []
        network_in_series = []
        network_out_series = []
        connections_series = []
        request_series = []
        latency_series = []

        current_day = start
        while current_day <= end:
            if base_util.get("cpu_avg") is not None:
                cpu_val = _deterministic_metric(resource_id, "cpu", current_day, base_util["cpu_avg"])
                cpu_series.append({"date": current_day.isoformat(), "value": min(cpu_val, 100.0)})

            if base_util.get("memory_avg") is not None:
                mem_val = _deterministic_metric(resource_id, "memory", current_day, base_util["memory_avg"])
                memory_series.append({"date": current_day.isoformat(), "value": min(mem_val, 100.0)})

            if base_util.get("disk_avg") is not None:
                disk_val = _deterministic_metric(resource_id, "disk", current_day, base_util["disk_avg"])
                disk_series.append({"date": current_day.isoformat(), "value": min(disk_val, 100.0)})

            # Network (MB)
            net_in = _deterministic_metric(resource_id, "net_in", current_day, 100.0 if base_util.get("cpu_avg") else 10.0)
            net_out = _deterministic_metric(resource_id, "net_out", current_day, 60.0 if base_util.get("cpu_avg") else 5.0)
            network_in_series.append({"date": current_day.isoformat(), "value": net_in})
            network_out_series.append({"date": current_day.isoformat(), "value": net_out})

            if ext_metrics.get("connections_avg") is not None:
                conn_val = _deterministic_metric(resource_id, "conn", current_day, ext_metrics["connections_avg"])
                connections_series.append({"date": current_day.isoformat(), "value": max(0, conn_val)})

            if ext_metrics.get("request_count_daily_avg") is not None:
                req_val = _deterministic_metric(resource_id, "req", current_day, ext_metrics["request_count_daily_avg"])
                request_series.append({"date": current_day.isoformat(), "value": max(0, req_val)})

            if ext_metrics.get("latency_avg_ms") is not None:
                lat_val = _deterministic_metric(resource_id, "lat", current_day, ext_metrics["latency_avg_ms"])
                latency_series.append({"date": current_day.isoformat(), "value": max(0, lat_val)})

            current_day += timedelta(days=1)

        return {
            "resource_id": resource_id,
            "cpu_utilization": cpu_series or None,
            "memory_utilization": memory_series or None,
            "disk_utilization": disk_series or None,
            "network_in_bytes": network_in_series,
            "network_out_bytes": network_out_series,
            "connections": connections_series or None,
            "request_count": request_series or None,
            "latency_ms": latency_series or None,
            "observation_days": (end - start).days + 1,
        }

    def get_all_resource_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        results = []
        end = end_date or reference_today()
        start = start_date or (end - timedelta(days=29))

        for resource in RESOURCES:
            rid = resource["resource_id"]
            base_util = RESOURCE_UTILIZATION.get(rid, {})
            ext_metrics = RESOURCE_EXTENDED_METRICS.get(rid, {})

            observation_days = (end - start).days + 1

            results.append({
                "resource_id": rid,
                "cpu_avg": base_util.get("cpu_avg"),
                "memory_avg": base_util.get("memory_avg"),
                "disk_avg": base_util.get("disk_avg"),
                "network_in_avg_mb": 100.0 if base_util.get("cpu_avg") else 10.0,
                "network_out_avg_mb": 60.0 if base_util.get("cpu_avg") else 5.0,
                "connections_avg": ext_metrics.get("connections_avg"),
                "request_count_daily_avg": ext_metrics.get("request_count_daily_avg"),
                "latency_avg_ms": ext_metrics.get("latency_avg_ms"),
                "observation_days": observation_days,
            })

        return results

    def get_data_freshness(self) -> MetricsFreshness:
        return MetricsFreshness(
            last_updated=datetime(2026, 8, 26, 11, 55, 0),
            status="FRESH",
        )

    def is_available(self) -> bool:
        return True
