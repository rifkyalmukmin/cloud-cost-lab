"""AI Cloud Cost Advisor.

Analyzes cost data and provides structured recommendations.
READ-ONLY — cannot take any destructive actions.

Uses a rule-based analysis engine (no external LLM dependency required).
When an LLM provider is configured, it can be used for natural language responses.
"""

from datetime import date
from typing import Optional

from app.ai.context import build_context
from app.ai.safety import sanitize_input, validate_question


class CostAdvisor:
    """AI-powered cost advisor — read-only analysis engine."""

    def analyze(self, question: str, reference_date: Optional[date] = None) -> dict:
        """Analyze a cost-related question and return structured response.

        Returns:
            dict with: summary, evidence, likely_cause, recommendation,
            potential_savings, risk, confidence
        """
        question = sanitize_input(question)
        is_valid, error = validate_question(question)
        if not is_valid:
            return {
                "summary": "Cannot process this request",
                "evidence": error,
                "likely_cause": None,
                "recommendation": None,
                "potential_savings": None,
                "risk": None,
                "confidence": None,
                "safety_note": "AI is read-only and cannot perform destructive actions",
            }

        context = build_context(reference_date)
        question_lower = question.lower()

        if any(kw in question_lower for kw in ["increase", "rose", "spike", "why did cost"]):
            return self._analyze_cost_increase(context)
        elif any(kw in question_lower for kw in ["save", "reduce", "optimize", "cut cost"]):
            return self._analyze_savings_opportunities(context)
        elif any(kw in question_lower for kw in ["idle", "unused", "which resource"]):
            return self._analyze_idle_resources(context)
        elif any(kw in question_lower for kw in ["anomal", "unexpected", "spike"]):
            return self._analyze_anomalies(context)
        elif any(kw in question_lower for kw in ["forecast", "predict", "future", "next month"]):
            return self._analyze_forecast(context)
        elif any(kw in question_lower for kw in ["priority", "first", "most important", "highest"]):
            return self._analyze_priority(context)
        elif any(kw in question_lower for kw in ["budget", "spend", "limit"]):
            return self._analyze_budget(context)
        else:
            return self._general_analysis(context)

    def _analyze_cost_increase(self, context: dict) -> dict:
        mom = context["cost"]["mom_change_percent"]
        top_service = context["cost_by_service"][0] if context["cost_by_service"] else None
        anomalies = context["anomalies"]

        if abs(mom) < 5:
            return {
                "summary": "No significant cost increase detected",
                "evidence": f"Month-over-month change is {mom:.1f}%, within normal variation",
                "likely_cause": "Normal cost fluctuation",
                "recommendation": "No action needed — costs are stable",
                "potential_savings": None,
                "risk": "LOW",
                "confidence": "HIGH",
                "safety_note": "AI is read-only and cannot perform destructive actions",
            }

        evidence_parts = [f"Month-over-month change: {mom:.1f}%"]
        if top_service:
            evidence_parts.append(f"Top service: {top_service['service']} (${top_service['cost']:.2f}, {top_service['percentage']}%)")
        if anomalies["total"] > 0:
            top_anomaly = anomalies["items"][0]
            evidence_parts.append(f"Anomaly detected on {top_anomaly['date']}: +{top_anomaly['percentage_change']:.0f}% ({top_anomaly['top_service']})")

        cause = "Increased usage across services"
        if anomalies["total"] > 0:
            cause = f"Cost spike detected — {anomalies['items'][0]['top_service']} on {anomalies['items'][0]['top_resource']}"

        return {
            "summary": f"Cost increased {mom:.1f}% compared to previous month",
            "evidence": "; ".join(evidence_parts),
            "likely_cause": cause,
            "recommendation": "Review top-spending services and investigate anomalies. Check for new resources or workload changes.",
            "potential_savings": context["savings_total"],
            "risk": "MEDIUM" if mom > 30 else "LOW",
            "confidence": "HIGH" if anomalies["total"] > 0 else "MEDIUM",
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }

    def _analyze_savings_opportunities(self, context: dict) -> dict:
        recommendations = context["recommendations"]
        low_util = context["utilization"]["low_utilization"]
        total_potential = sum(r["savings"] for r in recommendations)

        if not recommendations:
            return {
                "summary": "No significant savings opportunities identified",
                "evidence": "All resources appear to be appropriately sized based on current utilization",
                "likely_cause": None,
                "recommendation": "Continue monitoring. Review storage retention policies.",
                "potential_savings": 0,
                "risk": "LOW",
                "confidence": "MEDIUM",
                "safety_note": "AI is read-only and cannot perform destructive actions",
            }

        top_rec = recommendations[0]
        evidence_parts = [
            f"{len(recommendations)} optimization opportunities found",
            f"{low_util} resources with low utilization",
            f"Top: {top_rec['title']} on {top_rec['resource']} (${top_rec['savings']:.2f}/mo)",
        ]

        return {
            "summary": f"Found ${total_potential:.2f}/month in potential savings across {len(recommendations)} recommendations",
            "evidence": "; ".join(evidence_parts),
            "likely_cause": "Resources provisioned above actual demand",
            "recommendation": f"Start with highest priority: {top_rec['title']} ({top_rec['resource']}) — {top_rec['risk']} risk, {top_rec['confidence']} confidence",
            "potential_savings": round(total_potential, 2),
            "risk": top_rec["risk"],
            "confidence": top_rec["confidence"],
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }

    def _analyze_idle_resources(self, context: dict) -> dict:
        idle_resources = [
            r for r in context["utilization"]["resources"]
            if r["cpu_pattern"] == "low"
        ]

        if not idle_resources:
            return {
                "summary": "No idle resources detected",
                "evidence": "All compute resources show utilization above idle thresholds",
                "likely_cause": None,
                "recommendation": "No action needed",
                "potential_savings": None,
                "risk": "LOW",
                "confidence": "HIGH",
                "safety_note": "AI is read-only and cannot perform destructive actions",
            }

        total_waste = sum(r["monthly_cost"] for r in idle_resources)
        evidence_parts = [f"{len(idle_resources)} idle resource(s) detected"]
        for r in idle_resources[:3]:
            evidence_parts.append(f"{r['name']}: CPU {r['cpu_avg']}%, cost ${r['monthly_cost']:.2f}/mo")

        return {
            "summary": f"{len(idle_resources)} idle resource(s) costing ${total_waste:.2f}/month",
            "evidence": "; ".join(evidence_parts),
            "likely_cause": "Resources provisioned but not actively used",
            "recommendation": "Review each idle resource — consider scheduling (start/stop) or decommissioning if not needed",
            "potential_savings": round(total_waste * 0.9, 2),
            "risk": "LOW" if all(r["environment"] != "production" for r in idle_resources) else "MEDIUM",
            "confidence": "HIGH",
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }

    def _analyze_anomalies(self, context: dict) -> dict:
        anomalies = context["anomalies"]

        if anomalies["total"] == 0:
            return {
                "summary": "No cost anomalies detected in the analysis period",
                "evidence": "All daily costs are within expected range (z-score < 2.0)",
                "likely_cause": None,
                "recommendation": "No action needed — costs are stable",
                "potential_savings": None,
                "risk": "LOW",
                "confidence": "HIGH",
                "safety_note": "AI is read-only and cannot perform destructive actions",
            }

        top = anomalies["items"][0]
        return {
            "summary": f"{anomalies['total']} cost anomaly(ies) detected",
            "evidence": f"Largest spike on {top['date']}: actual ${top['actual']:.2f} vs expected ${top['expected']:.2f} (+{top['percentage_change']:.0f}%). Top contributor: {top['top_service']} ({top['top_resource']})",
            "likely_cause": f"Unusual activity on {top['top_resource']} ({top['top_service']})",
            "recommendation": "Investigate the resource for unexpected workload changes, configuration drift, or billing errors",
            "potential_savings": None,
            "risk": top["severity"],
            "confidence": "HIGH",
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }

    def _analyze_forecast(self, context: dict) -> dict:
        forecast = context["forecast"]
        budget = context["budget"]

        expected = forecast.get("monthly_expected")
        if expected is None:
            return {
                "summary": "Insufficient evidence",
                "evidence": "Not enough historical data to generate a reliable forecast",
                "likely_cause": None,
                "recommendation": "Wait for more billing data to accumulate (minimum 7 days)",
                "potential_savings": None,
                "risk": "LOW",
                "confidence": "LOW",
                "safety_note": "AI is read-only and cannot perform destructive actions",
            }

        budget_breach = expected > budget["limit"]

        return {
            "summary": f"Projected next-month cost: ${expected:.2f} (range: {forecast.get('monthly_range', 'N/A')})",
            "evidence": f"Based on {forecast['method']}. Budget: ${budget['limit']:.2f}, projected: ${expected:.2f}",
            "likely_cause": "Extrapolation from recent cost trend" if not budget_breach else "Spending trend exceeds budget limit",
            "recommendation": "Review optimization recommendations to reduce projected spend" if budget_breach else "Costs are within projected budget range",
            "potential_savings": None,
            "risk": "HIGH" if budget_breach else "LOW",
            "confidence": "MEDIUM",
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }

    def _analyze_priority(self, context: dict) -> dict:
        recommendations = context["recommendations"]

        if not recommendations:
            return {
                "summary": "No active recommendations",
                "evidence": "Recommendation engine produced no actionable items",
                "likely_cause": None,
                "recommendation": "System is well-optimized or insufficient data for analysis",
                "potential_savings": None,
                "risk": "LOW",
                "confidence": "MEDIUM",
                "safety_note": "AI is read-only and cannot perform destructive actions",
            }

        top = recommendations[0]
        return {
            "summary": f"Highest priority: {top['title']} (priority score: {top['priority']})",
            "evidence": f"Resource: {top['resource']}. Savings: ${top['savings']:.2f}/mo. Risk: {top['risk']}. Confidence: {top['confidence']}.",
            "likely_cause": "Resource identified by utilization analysis",
            "recommendation": f"Implement: {top['title']} on {top['resource']} — ${top['savings']:.2f}/mo savings with {top['risk']} risk",
            "potential_savings": top["savings"],
            "risk": top["risk"],
            "confidence": top["confidence"],
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }

    def _analyze_budget(self, context: dict) -> dict:
        budget = context["budget"]

        return {
            "summary": f"Budget status: {budget['status']} ({budget['utilization_pct']:.1f}% used)",
            "evidence": f"Limit: ${budget['limit']:.2f}, Current spend: ${budget['current_spend']:.2f}, Remaining: ${budget['limit'] - budget['current_spend']:.2f}. Projected status: {budget['projected_status']}",
            "likely_cause": None,
            "recommendation": "Implement cost-saving recommendations to reduce spend" if budget["status"] != "HEALTHY" else "Budget is healthy — no immediate action needed",
            "potential_savings": None,
            "risk": "HIGH" if budget["status"] == "EXCEEDED" else "MEDIUM" if budget["status"] in ["CRITICAL", "WARNING"] else "LOW",
            "confidence": "HIGH",
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }

    def _general_analysis(self, context: dict) -> dict:
        cost = context["cost"]
        recommendations = context["recommendations"]
        total_savings = sum(r["savings"] for r in recommendations)

        return {
            "summary": f"Current month: ${cost['current_month']:.2f} ({cost['mom_change_percent']:+.1f}% MoM). {len(recommendations)} optimization opportunities (${total_savings:.2f}/mo potential savings).",
            "evidence": f"Tracking {context['utilization']['total_resources']} resources. {context['utilization']['low_utilization']} underutilized. Budget: {context['budget']['status']}.",
            "likely_cause": None,
            "recommendation": "Ask a specific question: 'Why did cost increase?', 'Where can I save?', 'Which resource is idle?', 'What is my forecast?'",
            "potential_savings": round(total_savings, 2),
            "risk": "LOW",
            "confidence": "HIGH",
            "safety_note": "AI is read-only and cannot perform destructive actions",
        }


cost_advisor = CostAdvisor()
