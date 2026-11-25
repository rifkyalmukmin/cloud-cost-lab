"""AI Context builder.

Builds structured context for the AI advisor from application services.
Provides only the data needed to answer cost-related questions.
"""

from datetime import date
from typing import Optional

from app.ai.safety import filter_sensitive_data
from app.services.anomaly_service import anomaly_service
from app.services.budget_service import budget_service
from app.services.cost_service import cost_service
from app.services.forecast_service import forecast_service
from app.services.recommendation_service import recommendation_service
from app.services.utilization_service import utilization_service


def build_context(reference_date: Optional[date] = None) -> dict:
    """Build structured context for AI analysis.

    Gathers cost, utilization, recommendations, forecast, anomalies,
    and budget data into a single context dictionary.
    """
    ref = reference_date or date(2026, 8, 26)

    cost_summary = cost_service.get_summary(ref)
    cost_by_service = cost_service.get_by_service()
    cost_by_project = cost_service.get_by_project()

    util_summary = utilization_service.get_utilization_summary()

    recommendations = recommendation_service.generate_recommendations()
    savings_total = round(sum(item["potential_savings"] for item in recommendations), 2)

    forecast_data = forecast_service.forecast_cost(ref)

    anomalies_data = anomaly_service.detect_anomalies(ref)

    budget_data = budget_service.get_budget_status(ref)

    context = {
        "cost": {
            "current_month": cost_summary["current_month_cost"],
            "previous_month": cost_summary["previous_month_cost"],
            "mom_change_percent": cost_summary["mom_change_percent"],
            "projected": cost_summary["projected_month_cost"],
            "average_daily": cost_summary["average_daily_cost"],
        },
        "cost_by_service": [
            {"service": b["value"], "cost": b["net_cost"], "percentage": b["percentage"]}
            for b in cost_by_service["breakdown"]
        ],
        "cost_by_project": [
            {"project": b["value"], "cost": b["net_cost"], "percentage": b["percentage"]}
            for b in cost_by_project["breakdown"]
        ],
        "utilization": {
            "total_resources": util_summary["total_resources"],
            "low_utilization": util_summary["low_utilization_count"],
            "high_utilization": util_summary["high_utilization_count"],
            "resources": [
                {
                    "name": r["name"],
                    "service": r["service"],
                    "environment": r["environment"],
                    "cpu_avg": r["cpu"]["avg"],
                    "memory_avg": r["memory"]["avg"],
                    "monthly_cost": r["monthly_cost"],
                    "cpu_pattern": r["cpu_pattern"]["status"],
                }
                for r in util_summary["resources"]
            ],
        },
        "savings_total": savings_total,
        "recommendations": [
            {
                "title": r["title"],
                "resource": r["resource_name"],
                "savings": r["potential_savings"],
                "risk": r["risk"],
                "confidence": r["confidence"],
                "priority": r["priority"],
            }
            for r in recommendations[:10]
        ],
        "forecast": {
            "method": forecast_data.get("method", "unknown"),
            "monthly_expected": forecast_data.get("monthly_summary", {}).get("expected"),
            "monthly_range": forecast_data.get("monthly_summary", {}).get("range_description"),
        },
        "anomalies": {
            "total": anomalies_data.get("total_anomalies", 0),
            "items": [
                {
                    "date": a["date"],
                    "actual": a["actual"],
                    "expected": a["expected"],
                    "percentage_change": a["percentage_change"],
                    "severity": a["severity"],
                    "top_service": a["top_service"],
                    "top_resource": a["top_resource"],
                }
                for a in anomalies_data.get("anomalies", [])[:5]
            ],
        },
        "budget": {
            "limit": budget_data["budget"]["limit"],
            "current_spend": budget_data["current"]["spend"],
            "utilization_pct": budget_data["current"]["utilization_pct"],
            "status": budget_data["current"]["status"],
            "projected_status": budget_data["projected"]["status"],
        },
    }

    return filter_sensitive_data(context)
