"""Utilization analytics service.

Analyzes resource utilization patterns, computes statistics (avg, min, max, p95),
and identifies utilization issues (low, high, unstable, missing metrics).
"""

from datetime import date, timedelta
from typing import Any, Optional

from app.clock import reference_today
from app.services.mock_data import (
    BASE_DAILY_COSTS,
    RESOURCES,
    SERVICES,
    generate_cost_records,
    generate_utilization_records,
)


class UtilizationService:
    def _get_service_name(self, service_id: str) -> str:
        for s in SERVICES:
            if s["service_id"] == service_id:
                return s["service_name"]
        return service_id

    def _monthly_cost(self, resource_id: str) -> float:
        base_daily = BASE_DAILY_COSTS.get(resource_id, 0.0)
        return round(base_daily * 30, 2)

    def _compute_stats(self, values: list[float]) -> dict:
        """Compute avg, min, max, p95 for a list of values."""
        if not values:
            return {
                "avg": None,
                "min": None,
                "max": None,
                "p95": None,
            }

        sorted_vals = sorted(values)
        avg = sum(values) / len(values)
        minimum = sorted_vals[0]
        maximum = sorted_vals[-1]
        p95_idx = int(len(sorted_vals) * 0.95)
        p95 = sorted_vals[min(p95_idx, len(sorted_vals) - 1)]

        return {
            "avg": round(avg, 2),
            "min": round(minimum, 2),
            "max": round(maximum, 2),
            "p95": round(p95, 2),
        }

    def _analyze_pattern(self, stats: dict, metric_name: str) -> dict:
        """Analyze utilization pattern and identify issues."""
        if stats["avg"] is None:
            return {
                "status": "missing",
                "evidence": f"No {metric_name} metrics available for this resource",
            }

        avg = stats["avg"]
        max_val = stats["max"]
        min_val = stats["min"]
        variance = max_val - min_val

        if avg < 15:
            return {
                "status": "low",
                "evidence": f"Average {metric_name} is {avg}% — resource is underutilized",
            }
        elif avg > 85:
            return {
                "status": "high",
                "evidence": f"Average {metric_name} is {avg}% — resource may be overloaded",
            }
        elif variance > 60:
            return {
                "status": "unstable",
                "evidence": f"{metric_name} varies between {min_val}% and {max_val}% — unstable workload",
            }
        else:
            return {
                "status": "normal",
                "evidence": f"Average {metric_name} is {avg}% — within normal range",
            }

    def get_utilization_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Get aggregated utilization summary across all resources."""
        end = end_date or reference_today()
        start = start_date or (end - timedelta(days=29))

        resource_utilizations: list[dict[str, Any]] = []

        for resource in RESOURCES:
            rid = resource["resource_id"]
            util_records = generate_utilization_records(rid, start, end)

            if not util_records:
                continue

            cpu_vals = [r["cpu_utilization"] for r in util_records if r["cpu_utilization"] is not None]
            mem_vals = [r["memory_utilization"] for r in util_records if r["memory_utilization"] is not None]
            disk_vals = [r["disk_utilization"] for r in util_records if r["disk_utilization"] is not None]

            cpu_stats = self._compute_stats(cpu_vals)
            mem_stats = self._compute_stats(mem_vals)
            disk_stats = self._compute_stats(disk_vals)

            cpu_pattern = self._analyze_pattern(cpu_stats, "CPU")
            mem_pattern = self._analyze_pattern(mem_stats, "memory")

            resource_utilizations.append({
                "resource_id": rid,
                "name": resource["resource_name"],
                "service": self._get_service_name(resource["service_id"]),
                "environment": resource["environment"],
                "monthly_cost": self._monthly_cost(rid),
                "cpu": cpu_stats,
                "memory": mem_stats,
                "disk": disk_stats,
                "cpu_pattern": cpu_pattern,
                "memory_pattern": mem_pattern,
            })

        low_util = [r for r in resource_utilizations if r["cpu_pattern"]["status"] == "low"]
        high_util = [r for r in resource_utilizations if r["cpu_pattern"]["status"] == "high"]
        unstable = [r for r in resource_utilizations if r["cpu_pattern"]["status"] == "unstable"]
        missing = [r for r in resource_utilizations if r["cpu_pattern"]["status"] == "missing"]

        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_resources": len(resource_utilizations),
            "low_utilization_count": len(low_util),
            "high_utilization_count": len(high_util),
            "unstable_count": len(unstable),
            "missing_metrics_count": len(missing),
            "resources": resource_utilizations,
        }

    def get_resource_utilization(
        self,
        resource_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[dict]:
        """Get detailed utilization for a specific resource."""
        resource = None
        for r in RESOURCES:
            if r["resource_id"] == resource_id:
                resource = r
                break

        if resource is None:
            return None

        end = end_date or reference_today()
        start = start_date or (end - timedelta(days=29))

        util_records = generate_utilization_records(resource_id, start, end)

        if not util_records:
            return {
                "resource_id": resource_id,
                "name": resource["resource_name"],
                "service": self._get_service_name(resource["service_id"]),
                "environment": resource["environment"],
                "monthly_cost": self._monthly_cost(resource_id),
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "cpu": {"avg": None, "min": None, "max": None, "p95": None},
                "memory": {"avg": None, "min": None, "max": None, "p95": None},
                "disk": {"avg": None, "min": None, "max": None, "p95": None},
                "cpu_pattern": {"status": "missing", "evidence": "No CPU metrics available"},
                "memory_pattern": {"status": "missing", "evidence": "No memory metrics available"},
                "history": [],
            }

        cpu_vals = [r["cpu_utilization"] for r in util_records if r["cpu_utilization"] is not None]
        mem_vals = [r["memory_utilization"] for r in util_records if r["memory_utilization"] is not None]
        disk_vals = [r["disk_utilization"] for r in util_records if r["disk_utilization"] is not None]

        cpu_stats = self._compute_stats(cpu_vals)
        mem_stats = self._compute_stats(mem_vals)
        disk_stats = self._compute_stats(disk_vals)

        cpu_pattern = self._analyze_pattern(cpu_stats, "CPU")
        mem_pattern = self._analyze_pattern(mem_stats, "memory")

        return {
            "resource_id": resource_id,
            "name": resource["resource_name"],
            "service": self._get_service_name(resource["service_id"]),
            "environment": resource["environment"],
            "monthly_cost": self._monthly_cost(resource_id),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "cpu": cpu_stats,
            "memory": mem_stats,
            "disk": disk_stats,
            "cpu_pattern": cpu_pattern,
            "memory_pattern": mem_pattern,
            "history": util_records,
        }

    def get_cost_vs_utilization(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Get cost vs utilization data for visualization."""
        end = end_date or reference_today()
        start = start_date or end.replace(day=1)

        cost_records = generate_cost_records(start, end)

        resource_data = []
        for resource in RESOURCES:
            rid = resource["resource_id"]
            resource_costs = [c for c in cost_records if c["resource_id"] == rid]
            total_cost = sum(c["net_cost"] for c in resource_costs)

            util_records = generate_utilization_records(rid, start, end)
            cpu_vals = [r["cpu_utilization"] for r in util_records if r["cpu_utilization"] is not None]
            mem_vals = [r["memory_utilization"] for r in util_records if r["memory_utilization"] is not None]

            cpu_avg = round(sum(cpu_vals) / len(cpu_vals), 1) if cpu_vals else None
            mem_avg = round(sum(mem_vals) / len(mem_vals), 1) if mem_vals else None

            resource_data.append({
                "resource_id": rid,
                "name": resource["resource_name"],
                "service": self._get_service_name(resource["service_id"]),
                "environment": resource["environment"],
                "cost": round(total_cost, 2),
                "cpu_avg": cpu_avg,
                "memory_avg": mem_avg,
            })

        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "data": resource_data,
        }


utilization_service = UtilizationService()
