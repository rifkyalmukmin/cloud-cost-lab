"""Cost analytics service.

Aggregates cost data by various dimensions (service, project, environment)
and computes summaries, trends, and period comparisons.

Uses the BillingDataProvider abstraction to support both mock and real GCP data.
"""

from datetime import date, timedelta
from typing import Optional

from app.clock import SNAPSHOT_LABEL
from app.providers.base import BillingDataProvider
from app.providers.factory import create_billing_provider


class CostService:
    def __init__(self, provider: Optional[BillingDataProvider] = None):
        self._provider = provider
        self._records: Optional[list[dict]] = None

    @property
    def provider(self) -> BillingDataProvider:
        if self._provider is None:
            self._provider = create_billing_provider()
        return self._provider

    @property
    def records(self) -> list[dict]:
        if self._records is None:
            self._records = self.provider.get_cost_records()
        return self._records

    def get_data_freshness(self) -> dict:
        """Get data freshness status from the provider."""
        freshness = self.provider.get_data_freshness()
        return freshness.to_dict()

    def get_summary(self, reference_date: Optional[date] = None) -> dict:
        ref = reference_date or date(2026, 8, 26)

        current_month_start = ref.replace(day=1)
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        current_month_records = [
            r for r in self.records
            if current_month_start <= r["usage_date"] <= ref
        ]
        prev_month_records = [
            r for r in self.records
            if prev_month_start <= r["usage_date"] <= prev_month_end
        ]

        current_month_cost = sum(r["net_cost"] for r in current_month_records)
        prev_month_cost = sum(r["net_cost"] for r in prev_month_records)

        days_in_current = (ref - current_month_start).days + 1
        avg_daily = current_month_cost / max(days_in_current, 1)

        days_in_month = 30
        projected = avg_daily * days_in_month

        mom_change = 0.0
        if prev_month_cost > 0:
            mom_change = ((current_month_cost - prev_month_cost) / prev_month_cost) * 100

        potential_savings = self._deduped_potential_savings(ref)

        freshness = self.provider.get_data_freshness()

        return {
            "current_month_cost": round(current_month_cost, 2),
            "previous_month_cost": round(prev_month_cost, 2),
            "mom_change_percent": round(mom_change, 2),
            "average_daily_cost": round(avg_daily, 2),
            "projected_month_cost": round(projected, 2),
            "potential_savings": round(potential_savings, 2),
            "currency": "USD",
            "data_freshness": freshness.last_updated.isoformat() if freshness.last_updated else f"{ref.isoformat()}T04:00:00",
            "freshness_status": freshness.status,
            "snapshot_label": SNAPSHOT_LABEL,
        }

    def _deduped_potential_savings(self, reference_date: date) -> float:
        from app.services.recommendation_service import recommendation_service

        return recommendation_service.total_potential_savings(reference_date)

    def get_trend(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        end = end_date or date(2026, 8, 26)
        start = start_date or (end - timedelta(days=29))

        filtered = [
            r for r in self.records
            if start <= r["usage_date"] <= end
        ]

        daily_map: dict[date, dict] = {}
        for r in filtered:
            d = r["usage_date"]
            if d not in daily_map:
                daily_map[d] = {"date": d.isoformat(), "cost": 0.0, "net_cost": 0.0}
            daily_map[d]["cost"] += r["cost"]
            daily_map[d]["net_cost"] += r["net_cost"]

        daily_costs = sorted(daily_map.values(), key=lambda x: x["date"])
        for entry in daily_costs:
            entry["cost"] = round(entry["cost"], 2)
            entry["net_cost"] = round(entry["net_cost"], 2)

        total = sum(entry["net_cost"] for entry in daily_costs)

        return {
            "daily_costs": daily_costs,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_cost": round(total, 2),
        }

    def get_by_service(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        end = end_date or date(2026, 8, 26)
        start = start_date or end.replace(day=1)

        filtered = [
            r for r in self.records
            if start <= r["usage_date"] <= end
        ]

        service_map: dict[str, float] = {}
        for r in filtered:
            name = r["service_name"]
            service_map[name] = service_map.get(name, 0.0) + r["net_cost"]

        total = sum(service_map.values())
        breakdown = [
            {
                "dimension": "service",
                "value": name,
                "total_cost": round(cost, 2),
                "net_cost": round(cost, 2),
                "percentage": round((cost / total) * 100, 1) if total > 0 else 0.0,
            }
            for name, cost in sorted(service_map.items(), key=lambda x: -x[1])
        ]

        return {
            "breakdown": breakdown,
            "total_cost": round(total, 2),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }

    def get_by_project(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        end = end_date or date(2026, 8, 26)
        start = start_date or end.replace(day=1)

        filtered = [
            r for r in self.records
            if start <= r["usage_date"] <= end
        ]

        project_map: dict[str, float] = {}
        for r in filtered:
            name = r["project_name"]
            project_map[name] = project_map.get(name, 0.0) + r["net_cost"]

        total = sum(project_map.values())
        breakdown = [
            {
                "dimension": "project",
                "value": name,
                "total_cost": round(cost, 2),
                "net_cost": round(cost, 2),
                "percentage": round((cost / total) * 100, 1) if total > 0 else 0.0,
            }
            for name, cost in sorted(project_map.items(), key=lambda x: -x[1])
        ]

        return {
            "breakdown": breakdown,
            "total_cost": round(total, 2),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }

    def get_by_environment(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        end = end_date or date(2026, 8, 26)
        start = start_date or end.replace(day=1)

        filtered = [
            r for r in self.records
            if start <= r["usage_date"] <= end
        ]

        env_map: dict[str, float] = {}
        for r in filtered:
            env = r["environment"] or "UNALLOCATED"
            env_map[env] = env_map.get(env, 0.0) + r["net_cost"]

        total = sum(env_map.values())
        breakdown = [
            {
                "dimension": "environment",
                "value": name,
                "total_cost": round(cost, 2),
                "net_cost": round(cost, 2),
                "percentage": round((cost / total) * 100, 1) if total > 0 else 0.0,
            }
            for name, cost in sorted(env_map.items(), key=lambda x: -x[1])
        ]

        return {
            "breakdown": breakdown,
            "total_cost": round(total, 2),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }


cost_service = CostService()
