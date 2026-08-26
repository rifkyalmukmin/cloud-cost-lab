"""Monitoring service.

Correlates cost, utilization, and performance metrics to provide
enriched evidence for resource optimization recommendations.
"""

from datetime import date, timedelta
from typing import Optional

from app.providers.monitoring_base import MonitoringDataProvider
from app.providers.monitoring_factory import create_monitoring_provider
from app.services.mock_data import BASE_DAILY_COSTS, RESOURCES, SERVICES


class MonitoringService:
    def __init__(self, provider: Optional[MonitoringDataProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> MonitoringDataProvider:
        if self._provider is None:
            self._provider = create_monitoring_provider()
        return self._provider

    def _get_service_name(self, service_id: str) -> str:
        for s in SERVICES:
            if s["service_id"] == service_id:
                return s["service_name"]
        return service_id

    def _monthly_cost(self, resource_id: str) -> float:
        return round(BASE_DAILY_COSTS.get(resource_id, 0.0) * 30, 2)

    def get_enriched_resource_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Get all resource metrics enriched with cost data and evidence strength."""
        end = end_date or date(2026, 8, 26)
        start = start_date or (end - timedelta(days=29))

        all_metrics = self.provider.get_all_resource_metrics(start, end)
        freshness = self.provider.get_data_freshness()

        enriched = []
        for metrics in all_metrics:
            rid = metrics["resource_id"]
            resource = next((r for r in RESOURCES if r["resource_id"] == rid), None)
            if resource is None:
                continue

            monthly_cost = self._monthly_cost(rid)
            observation_days = metrics.get("observation_days", 0)

            evidence_strength = self._assess_evidence_strength(metrics, observation_days)

            enriched.append({
                "resource_id": rid,
                "resource_name": resource["resource_name"],
                "service": self._get_service_name(resource["service_id"]),
                "environment": resource["environment"],
                "monthly_cost": monthly_cost,
                "metrics": {
                    "cpu_avg": metrics.get("cpu_avg"),
                    "memory_avg": metrics.get("memory_avg"),
                    "disk_avg": metrics.get("disk_avg"),
                    "network_in_avg_mb": metrics.get("network_in_avg_mb"),
                    "network_out_avg_mb": metrics.get("network_out_avg_mb"),
                    "connections_avg": metrics.get("connections_avg"),
                    "request_count_daily_avg": metrics.get("request_count_daily_avg"),
                    "latency_avg_ms": metrics.get("latency_avg_ms"),
                },
                "observation_days": observation_days,
                "evidence_strength": evidence_strength,
            })

        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "monitoring_freshness": freshness.to_dict(),
            "resources": enriched,
        }

    def get_resource_detail_metrics(
        self,
        resource_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[dict]:
        """Get detailed metrics for a single resource (with time series)."""
        metrics = self.provider.get_resource_metrics(resource_id, start_date, end_date)
        if metrics is None:
            return None

        resource = next((r for r in RESOURCES if r["resource_id"] == resource_id), None)
        if resource is None:
            return None

        monthly_cost = self._monthly_cost(resource_id)
        observation_days = metrics.get("observation_days", 0)

        cpu_series = metrics.get("cpu_utilization") or []
        cpu_values = [p["value"] for p in cpu_series]
        cpu_avg = round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else None

        mem_series = metrics.get("memory_utilization") or []
        mem_values = [p["value"] for p in mem_series]
        mem_avg = round(sum(mem_values) / len(mem_values), 2) if mem_values else None

        evidence_strength = self._assess_evidence_strength(
            {"cpu_avg": cpu_avg, "memory_avg": mem_avg, "observation_days": observation_days},
            observation_days,
        )

        return {
            "resource_id": resource_id,
            "resource_name": resource["resource_name"],
            "service": self._get_service_name(resource["service_id"]),
            "environment": resource["environment"],
            "monthly_cost": monthly_cost,
            "observation_days": observation_days,
            "evidence_strength": evidence_strength,
            "summary": {
                "cpu_avg": cpu_avg,
                "memory_avg": mem_avg,
            },
            "time_series": {
                "cpu_utilization": metrics.get("cpu_utilization"),
                "memory_utilization": metrics.get("memory_utilization"),
                "disk_utilization": metrics.get("disk_utilization"),
                "network_in_bytes": metrics.get("network_in_bytes"),
                "network_out_bytes": metrics.get("network_out_bytes"),
                "connections": metrics.get("connections"),
                "request_count": metrics.get("request_count"),
                "latency_ms": metrics.get("latency_ms"),
            },
        }

    def _assess_evidence_strength(self, metrics: dict, observation_days: int) -> str:
        """Assess how strong the monitoring evidence is.

        Factors:
        - Duration of observation (longer = stronger)
        - Availability of metrics (more metrics = stronger)

        Returns: "STRONG", "MODERATE", "WEAK", or "INSUFFICIENT"
        """
        if observation_days < 3:
            return "INSUFFICIENT"

        available_metrics = 0
        if metrics.get("cpu_avg") is not None:
            available_metrics += 1
        if metrics.get("memory_avg") is not None:
            available_metrics += 1
        if metrics.get("disk_avg") is not None:
            available_metrics += 1

        if observation_days >= 14 and available_metrics >= 2:
            return "STRONG"
        elif observation_days >= 7 and available_metrics >= 1:
            return "MODERATE"
        elif observation_days >= 3:
            return "WEAK"
        else:
            return "INSUFFICIENT"


monitoring_service = MonitoringService()
