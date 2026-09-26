"""Deterministic advisor (default provider, ADR-003/ADR-008).

Answers are composed from the structured context with keyword intent
detection. Fully offline, reproducible, and safe by construction: it never
executes anything and answers "Insufficient evidence" whenever the context
lacks the data a question needs.
"""

from __future__ import annotations

from costlab.ai.base import (
    UNSUPPORTED_QUESTION,
    AdvisorAnswer,
    AdvisorContext,
    AIAdvisorProvider,
    is_injection_attempt,
)

SUPPORTED = (
    "why_cost_increase",
    "where_save",
    "which_resource_optimize",
    "anomaly_cause",
    "forecast",
    "highest_priority",
)


def _detect_intent(question: str) -> str | None:
    lowered = question.lower()
    if "anomal" in lowered or ("what caused" in lowered and "cost" in lowered):
        return "anomaly_cause"
    if "forecast" in lowered or "next month" in lowered or "projection" in lowered:
        return "forecast"
    if "increase" in lowered or "spike" in lowered or ("why" in lowered and "cost" in lowered):
        return "why_cost_increase"
    if "highest priority" in lowered or "priority" in lowered:
        return "highest_priority"
    if "which resource" in lowered or ("optimize" in lowered and "resource" in lowered):
        return "which_resource_optimize"
    if "save" in lowered or "reduce" in lowered:
        return "where_save"
    return None


class MockAdvisorProvider(AIAdvisorProvider):
    """Deterministic, offline advisor — the default and CI-safe provider."""

    name = "mock"

    def answer(self, question: str, context: AdvisorContext) -> AdvisorAnswer:
        if is_injection_attempt(question):
            return AdvisorAnswer(
                intent="refused_injection",
                sections={
                    "summary": (
                        "The question contains instruction-override or action language. "
                        "Refused as a prompt-injection attempt."
                    ),
                    "evidence": [],
                    "likely_cause": "Untrusted instruction text in the question.",
                    "recommendation": (
                        "Rephrase as a cost question. The advisor is read-only and has no "
                        "execution capability in any case."
                    ),
                    "potential_savings": None,
                    "risk": "none",
                    "confidence": "HIGH",
                },
                mode=self.name,
            )

        intent = _detect_intent(question)
        if intent is None:
            return AdvisorAnswer(
                intent="unsupported",
                sections={
                    "summary": UNSUPPORTED_QUESTION,
                    "evidence": [],
                    "likely_cause": None,
                    "recommendation": "Ask one of the supported cost questions.",
                    "potential_savings": None,
                    "risk": "none",
                    "confidence": "LOW",
                },
                mode=self.name,
            )
        handler = {
            "why_cost_increase": self._why_cost_increase,
            "where_save": self._where_save,
            "which_resource_optimize": self._which_resource,
            "anomaly_cause": self._anomaly_cause,
            "forecast": self._forecast,
            "highest_priority": self._highest_priority,
        }[intent]
        return handler(context)

    # -- intents ----------------------------------------------------------

    def _why_cost_increase(self, context: AdvisorContext) -> AdvisorAnswer:
        anomalies = context.anomalies.get("recent", [])
        if not anomalies:
            return self._insufficient(
                "why cost increased",
                "No anomalies were detected in the analysis window: no single day rose "
                "above the rolling baseline by more than the noise floor.",
            )
        top = anomalies[0]
        sections = {
            "summary": (
                f"Cost increased on {top['date']}: {top['resource']} ran at "
                f"${top['actual']:.2f} versus an expected ${top['expected']:.2f} "
                f"(+{top['percentage_change']:.0f}%, severity {top['severity']})."
            ),
            "evidence": [
                f"actual ${top['actual']:.2f} vs expected ${top['expected']:.2f} "
                f"(difference +${top['difference']:.2f})",
                f"percentage change +{top['percentage_change']:.0f}%",
                f"z-score {top['z_score']}",
            ],
            "likely_cause": (
                "A run-rate change around that date — new/changed resources, traffic, or "
                "configuration. The platform cannot attribute cause; investigate the "
                "resource's activity that day."
            ),
            "recommendation": (
                "Open the resource detail view for the day in question and compare "
                "configuration/usage; if the increase is unwanted, use the matching "
                "recommendation and its approval workflow."
            ),
            "potential_savings": round(top["difference"] * 30.0, 2),
            "risk": "low (investigation only)",
            "confidence": "MEDIUM" if top["z_score"] else "LOW",
        }
        return AdvisorAnswer("why_cost_increase", sections, self.name)

    def _where_save(self, context: AdvisorContext) -> AdvisorAnswer:
        recs = context.recommendations.get("top", [])
        if not recs:
            return self._insufficient(
                "where to save",
                "No recommendations exist yet — run the analysis and ensure utilization "
                "data is present.",
            )
        total = sum(r["potential_savings"] for r in recs)
        sections = {
            "summary": (
                f"{context.recommendations.get('total', len(recs))} evidence-backed "
                f"recommendations exist, worth about ${total:.2f}/month in potential "
                "savings (estimates)."
            ),
            "evidence": [
                f"{r['title']} on {r['resource']}: ${r['potential_savings']:.2f}/month, "
                f"risk {r['risk']}, confidence {r['confidence']}"
                for r in recs
            ],
            "likely_cause": "Sustained low utilization or measured cost run-rate changes.",
            "recommendation": (
                "Start with the highest-priority item on the Recommendations page; "
                "approval is required before any change."
            ),
            "potential_savings": round(total, 2),
            "risk": "varies per recommendation",
            "confidence": "MEDIUM",
        }
        return AdvisorAnswer("where_save", sections, self.name)

    def _which_resource(self, context: AdvisorContext) -> AdvisorAnswer:
        low = context.utilization.get("low_utilization", [])
        recs = context.recommendations.get("top", [])
        if not low or not recs:
            return self._insufficient(
                "which resource to optimize",
                "No low-utilization resource with cost evidence was found in the window.",
            )
        target = low[0]
        sections = {
            "summary": (
                f"Optimize {target} first: it shows sustained low CPU utilization "
                "while accruing cost."
            ),
            "evidence": [
                "listed under low_utilization (avg CPU < 20%)",
                "matching recommendation(s): "
                + ", ".join(r["title"] for r in recs if r["resource"] == target or True),
            ],
            "likely_cause": "Overprovisioned shape or a workload that shrank/moved.",
            "recommendation": (
                "Review the resource detail and the linked recommendation; verify with "
                "the owner before any change."
            ),
            "potential_savings": None,
            "risk": "low-medium (confirm the workload is not periodic)",
            "confidence": "MEDIUM",
        }
        return AdvisorAnswer("which_resource_optimize", sections, self.name)

    def _anomaly_cause(self, context: AdvisorContext) -> AdvisorAnswer:
        anomalies = context.anomalies.get("recent", [])
        if not anomalies:
            return self._insufficient(
                "the anomaly's cause",
                "No cost anomalies were detected in the analysis window.",
            )
        top = anomalies[0]
        sections = {
            "summary": (
                f"The most significant anomaly is on {top['date']} for {top['resource']}: "
                f"+{top['percentage_change']:.0f}% versus the 14-day baseline."
            ),
            "evidence": [
                f"actual ${top['actual']:.2f} / expected ${top['expected']:.2f}",
                f"z-score {top['z_score']}, severity {top['severity']}",
            ],
            "likely_cause": (
                "Determining the true cause requires data the platform does not have "
                "(deployments, traffic shifts). Insufficient evidence beyond the measured jump."
            ),
            "recommendation": (
                "Correlate the date with deployments or configuration changes; the "
                "recommendation engine turns sustained runs into actionable findings."
            ),
            "potential_savings": None,
            "risk": "unknown",
            "confidence": "MEDIUM",
        }
        return AdvisorAnswer("anomaly_cause", sections, self.name)

    def _forecast(self, context: AdvisorContext) -> AdvisorAnswer:
        fc = context.forecast
        if not fc.get("sufficient_data"):
            return self._insufficient(
                "a forecast",
                f"Insufficient data: {fc}.",
            )
        totals = fc.get("totals") or {}
        sections = {
            "summary": (
                f"Next 30 days expected at ${totals.get('expected_30d', 0):.2f} "
                f"(range ${totals.get('lower_bound_30d', 0):.2f} – "
                f"${totals.get('upper_bound_30d', 0):.2f}), trend {fc.get('trend')}."
            ),
            "evidence": [
                f"moving average + linear trend blend, confidence {fc.get('confidence')}",
                "history-based projection, interval 80%",
            ],
            "likely_cause": None,
            "recommendation": (
                "Treat the range as the honest expectation; compare against your budget "
                "on the Budget page."
            ),
            "potential_savings": None,
            "risk": "projection uncertainty grows with the horizon",
            "confidence": fc.get("confidence") or "LOW",
        }
        return AdvisorAnswer("forecast", sections, self.name)

    def _highest_priority(self, context: AdvisorContext) -> AdvisorAnswer:
        recs = context.recommendations.get("top", [])
        if not recs:
            return self._insufficient(
                "priority ranking",
                "No recommendations exist — nothing to rank.",
            )
        top = recs[0]
        sections = {
            "summary": (
                f"Highest priority: {top['title']} on {top['resource']} "
                f"(priority score {top['priority_score']}, "
                f"${top['potential_savings']:.2f}/month potential)."
            ),
            "evidence": [
                f"priority score {top['priority_score']} — project-specific heuristic "
                "(savings, confidence, risk, effort)",
                f"risk {top['risk']} · confidence {top['confidence']} · status {top['status']}",
            ],
            "likely_cause": None,
            "recommendation": (
                "Review its evidence on the Recommendations page and approve only after "
                "human verification. The platform never acts automatically."
            ),
            "potential_savings": top["potential_savings"],
            "risk": top["risk"],
            "confidence": top["confidence"],
        }
        return AdvisorAnswer("highest_priority", sections, self.name)

    @staticmethod
    def _insufficient(about: str, reason: str) -> AdvisorAnswer:
        return AdvisorAnswer(
            intent="insufficient_evidence",
            sections={
                "summary": f"Insufficient evidence to answer the question about {about}.",
                "evidence": [reason],
                "likely_cause": None,
                "recommendation": "Collect more data or broaden the analysis window.",
                "potential_savings": None,
                "risk": "none",
                "confidence": "LOW",
            },
            mode="mock",
        )
