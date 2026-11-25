"""Budget monitoring service.

Tracks spending against budgets and generates alerts when thresholds are breached.
No automatic destructive actions — only warnings and recommendations.
"""

from datetime import date
from typing import Optional

from app.services.cost_service import cost_service


class BudgetService:
    def __init__(self):
        # Demo budget configuration
        self.budget = {
            "id": "monthly-budget-001",
            "name": "Monthly Cloud Budget",
            "scope": "global",
            "period": "monthly",
            "limit": 500.0,
            "warning_threshold": 70.0,
            "critical_threshold": 90.0,
            "currency": "USD",
        }

    def _calculate_status(self, utilization_pct: float) -> str:
        """Determine budget status based on utilization percentage."""
        if utilization_pct >= 100.0:
            return "EXCEEDED"
        elif utilization_pct >= self.budget["critical_threshold"]:
            return "CRITICAL"
        elif utilization_pct >= self.budget["warning_threshold"]:
            return "WARNING"
        else:
            return "HEALTHY"

    def get_budget_status(
        self,
        reference_date: Optional[date] = None,
    ) -> dict:
        """Get current budget status with spending, utilization, and alerts."""
        ref = reference_date or date(2026, 8, 26)

        summary = cost_service.get_summary(ref)
        current_spend = summary["current_month_cost"]
        projected_spend = summary["projected_month_cost"]

        budget_limit = self.budget["limit"]
        utilization_pct = (current_spend / budget_limit) * 100 if budget_limit > 0 else 0
        projected_utilization_pct = (projected_spend / budget_limit) * 100 if budget_limit > 0 else 0

        remaining = max(0, budget_limit - current_spend)
        status = self._calculate_status(utilization_pct)

        projected_status = self._calculate_status(projected_utilization_pct)

        alerts = []
        if status == "EXCEEDED":
            alerts.append({
                "severity": "CRITICAL",
                "message": f"Budget exceeded by ${current_spend - budget_limit:.2f}",
                "recommendation": "Review spending immediately. Identify high-cost resources and implement cost-saving recommendations.",
            })
        elif status == "CRITICAL":
            alerts.append({
                "severity": "CRITICAL",
                "message": f"Budget utilization at {utilization_pct:.1f}% (critical threshold: {self.budget['critical_threshold']}%)",
                "recommendation": "Budget breach imminent. Pause non-essential resource creation and review optimization opportunities.",
            })
        elif status == "WARNING":
            alerts.append({
                "severity": "WARNING",
                "message": f"Budget utilization at {utilization_pct:.1f}% (warning threshold: {self.budget['warning_threshold']}%)",
                "recommendation": "Monitor spending closely and review cost optimization recommendations.",
            })

        if projected_status in ["EXCEEDED", "CRITICAL"] and status not in ["EXCEEDED", "CRITICAL"]:
            alerts.append({
                "severity": "WARNING",
                "message": f"Projected to reach {projected_utilization_pct:.1f}% by month end",
                "recommendation": "Current spending trend will breach budget. Consider implementing cost-saving measures now.",
            })

        return {
            "budget": {
                "id": self.budget["id"],
                "name": self.budget["name"],
                "scope": self.budget["scope"],
                "period": self.budget["period"],
                "limit": budget_limit,
                "warning_threshold": self.budget["warning_threshold"],
                "critical_threshold": self.budget["critical_threshold"],
                "currency": self.budget["currency"],
            },
            "current": {
                "spend": round(current_spend, 2),
                "utilization_pct": round(utilization_pct, 2),
                "remaining": round(remaining, 2),
                "status": status,
            },
            "projected": {
                "spend": round(projected_spend, 2),
                "utilization_pct": round(projected_utilization_pct, 2),
                "status": projected_status,
            },
            "alerts": alerts,
            "period_start": summary["data_freshness"][:10],
            "period_end": ref.replace(day=1).replace(month=ref.month % 12 + 1).isoformat() if ref.month < 12 else ref.replace(year=ref.year + 1, month=1, day=1).isoformat(),
        }


budget_service = BudgetService()
