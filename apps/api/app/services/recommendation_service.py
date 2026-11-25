"""Recommendation service.

Evaluates resources against recommendation rules and generates
evidence-based optimization recommendations.
"""

import hashlib
from datetime import date, timedelta
from typing import Optional

from app.recommendations.rules import ALL_RULES
from app.services.mock_data import BASE_DAILY_COSTS, RESOURCES, SERVICES
from app.services.utilization_service import utilization_service


def cost_change_percent(
    records: list[dict],
    resource_id: str,
    end: date,
    window_days: int = 14,
) -> float:
    """Percent change of the latest window versus the window before it."""
    recent_start = end - timedelta(days=window_days - 1)
    prior_end = recent_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=window_days - 1)
    recent = 0.0
    prior = 0.0
    for record in records:
        if record.get("resource_id") != resource_id:
            continue
        usage = record["usage_date"]
        amount = float(record.get("net_cost") or 0)
        if recent_start <= usage <= end:
            recent += amount
        elif prior_start <= usage <= prior_end:
            prior += amount
    if prior <= 0:
        return 0.0
    return round(((recent - prior) / prior) * 100, 2)


def _outranks(candidate: dict, incumbent: dict) -> bool:
    if candidate["priority"] != incumbent["priority"]:
        return candidate["priority"] > incumbent["priority"]
    if candidate["potential_savings"] != incumbent["potential_savings"]:
        return candidate["potential_savings"] > incumbent["potential_savings"]
    return candidate["rule"] < incumbent["rule"]


def dedupe_by_resource(recommendations: list[dict]) -> list[dict]:
    """Keep one winning rule per resource so savings are not summed twice."""
    chosen: dict[str, dict] = {}
    for recommendation in recommendations:
        current = chosen.get(recommendation["resource_id"])
        if current is None or _outranks(recommendation, current):
            chosen[recommendation["resource_id"]] = recommendation
    deduped = list(chosen.values())
    deduped.sort(key=lambda item: item["priority"], reverse=True)
    return deduped


class RecommendationService:
    def _get_service_name(self, service_id: str) -> str:
        for s in SERVICES:
            if s["service_id"] == service_id:
                return s["service_name"]
        return service_id

    def _monthly_cost(self, resource_id: str) -> float:
        base_daily = BASE_DAILY_COSTS.get(resource_id, 0.0)
        return round(base_daily * 30, 2)

    def _generate_id(self, resource_id: str, rule_name: str) -> str:
        """Generate deterministic recommendation ID."""
        key = f"{resource_id}:{rule_name}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def generate_recommendations(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Generate all recommendations by evaluating resources against rules."""
        end = end_date or date(2026, 8, 26)
        start = start_date or (end - timedelta(days=29))

        util_summary = utilization_service.get_utilization_summary(start, end)
        recommendations = []

        for resource_util in util_summary["resources"]:
            resource_id = resource_util["resource_id"]
            resource_raw = next((r for r in RESOURCES if r["resource_id"] == resource_id), None)
            if not resource_raw:
                continue

            resource_data = {
                "resource_id": resource_id,
                "name": resource_util["name"],
                "service": resource_util["service"],
                "environment": resource_util["environment"],
                "monthly_cost": resource_util["monthly_cost"],
                "status": resource_raw.get("status", "active"),
            }

            metrics_data = {
                "cpu_avg": resource_util["cpu"]["avg"],
                "memory_avg": resource_util["memory"]["avg"],
                "disk_avg": resource_util["disk"]["avg"],
                "cost_change_pct": self._cost_change_pct(resource_id, end),
            }

            for rule in ALL_RULES:
                if rule.evaluate(resource_data, metrics_data):
                    explanation = rule.explain(resource_data, metrics_data)
                    saving = rule.calculate_saving(resource_data, metrics_data)
                    risk = rule.calculate_risk(resource_data, metrics_data)
                    conf = rule.confidence(resource_data, metrics_data)
                    eff = rule.effort(resource_data, metrics_data)
                    priority = rule.priority_score(resource_data, metrics_data)

                    potential_cost = resource_data["monthly_cost"] - saving
                    savings_pct = (saving / resource_data["monthly_cost"] * 100) if resource_data["monthly_cost"] > 0 else 0

                    recommendations.append({
                        "id": self._generate_id(resource_id, rule.__class__.__name__),
                        "rule": rule.__class__.__name__,
                        "title": explanation["title"],
                        "resource_id": resource_id,
                        "resource_name": resource_data["name"],
                        "service": resource_data["service"],
                        "environment": resource_data["environment"],
                        "problem": explanation["problem"],
                        "evidence": explanation["evidence"],
                        "recommendation": explanation["recommendation"],
                        "current_cost": resource_data["monthly_cost"],
                        "potential_cost": round(potential_cost, 2),
                        "potential_savings": saving,
                        "savings_percentage": round(savings_pct, 1),
                        "risk": risk,
                        "confidence": conf,
                        "effort": eff,
                        "priority": priority,
                        "status": "OPEN",
                        "approval_required": True,
                    })

        return dedupe_by_resource(recommendations)

    def _cost_change_pct(self, resource_id: str, end: date) -> float:
        from app.services.cost_service import cost_service

        return cost_change_percent(cost_service.records, resource_id, end)

    def total_potential_savings(self, reference_date: Optional[date] = None) -> float:
        """Sum potential savings after one winning recommendation per resource."""
        recommendations = self.generate_recommendations(end_date=reference_date)
        return round(sum(item["potential_savings"] for item in recommendations), 2)

    def get_recommendation(self, recommendation_id: str) -> Optional[dict]:
        """Get a specific recommendation by ID."""
        recommendations = self.generate_recommendations()
        for rec in recommendations:
            if rec["id"] == recommendation_id:
                return rec
        return None


recommendation_service = RecommendationService()
