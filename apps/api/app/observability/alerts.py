"""Alerting rules based on SLI/SLO breaches.

Generates alerts when:
- Billing data becomes stale (> 36h)
- API error rate exceeds threshold
- Recommendation engine fails
- Forecast engine fails
"""

from app.observability.metrics import metrics


ALERT_RULES = [
    {
        "name": "BillingDataStale",
        "condition": "billing_data_freshness_seconds > 129600",
        "severity": "WARNING",
        "description": "Billing data is older than 36 hours",
        "runbook": "docs/runbooks/billing-stale.md",
    },
    {
        "name": "BillingDataCritical",
        "condition": "billing_data_freshness_seconds > 172800",
        "severity": "CRITICAL",
        "description": "Billing data is older than 48 hours",
        "runbook": "docs/runbooks/billing-stale.md",
    },
    {
        "name": "APIHighErrorRate",
        "condition": "error_rate > 5%",
        "severity": "CRITICAL",
        "description": "API error rate exceeds 5%",
        "runbook": "docs/runbooks/api-outage.md",
    },
    {
        "name": "RecommendationFailure",
        "condition": "recommendations_failed_total > 0",
        "severity": "WARNING",
        "description": "Recommendation engine encountered failures",
        "runbook": "docs/runbooks/recommendation-failure.md",
    },
    {
        "name": "ForecastFailure",
        "condition": "forecast_failed_total > 0",
        "severity": "WARNING",
        "description": "Forecast engine encountered failures",
        "runbook": "docs/runbooks/forecast-failure.md",
    },
]


def evaluate_alerts() -> list[dict]:
    """Evaluate all alert rules and return active alerts."""
    active_alerts = []

    freshness = metrics.get_gauge("billing_data_freshness_seconds")
    if freshness > 172800:
        active_alerts.append({
            "name": "BillingDataCritical",
            "severity": "CRITICAL",
            "message": f"Billing data is {freshness / 3600:.1f} hours old (threshold: 48h)",
            "runbook": "docs/runbooks/billing-stale.md",
        })
    elif freshness > 129600:
        active_alerts.append({
            "name": "BillingDataStale",
            "severity": "WARNING",
            "message": f"Billing data is {freshness / 3600:.1f} hours old (threshold: 36h)",
            "runbook": "docs/runbooks/billing-stale.md",
        })

    all_metrics = metrics.get_all()
    total_requests = 0
    error_requests = 0
    for key, value in all_metrics["counters"].items():
        if key.startswith("http_requests_total"):
            total_requests += value
            if "status=5" in key or "status=4" in key:
                error_requests += value

    if total_requests > 100:
        error_rate = error_requests / total_requests * 100
        if error_rate > 5.0:
            active_alerts.append({
                "name": "APIHighErrorRate",
                "severity": "CRITICAL",
                "message": f"API error rate is {error_rate:.1f}% (threshold: 5%)",
                "runbook": "docs/runbooks/api-outage.md",
            })

    rec_failures = metrics.get_counter("recommendations_failed_total")
    if rec_failures > 0:
        active_alerts.append({
            "name": "RecommendationFailure",
            "severity": "WARNING",
            "message": f"Recommendation engine has {rec_failures} failure(s)",
            "runbook": "docs/runbooks/recommendation-failure.md",
        })

    forecast_failures = metrics.get_counter("forecast_failed_total")
    if forecast_failures > 0:
        active_alerts.append({
            "name": "ForecastFailure",
            "severity": "WARNING",
            "message": f"Forecast engine has {forecast_failures} failure(s)",
            "runbook": "docs/runbooks/forecast-failure.md",
        })

    return active_alerts
