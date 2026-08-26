from fastapi import APIRouter

from app.observability.alerts import ALERT_RULES, evaluate_alerts
from app.observability.metrics import metrics
from app.observability.sli import get_slo_status

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/metrics")
def get_metrics():
    """Get current application metrics."""
    return metrics.get_all()


@router.get("/slo")
def get_slo():
    """Get SLI/SLO compliance status."""
    return get_slo_status()


@router.get("/alerts")
def get_alerts():
    """Get active alerts based on current metrics."""
    active = evaluate_alerts()
    return {
        "active_alerts": active,
        "total_active": len(active),
        "alert_rules": ALERT_RULES,
    }
