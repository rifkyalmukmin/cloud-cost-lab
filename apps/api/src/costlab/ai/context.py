"""Builds the structured, whitelisted context the advisor reasons over.

Every value comes from the platform's own analytics (cost, utilization,
recommendations, anomalies, forecast, budget) — bounded lists only, no raw
database rows, no credentials, no free-form user content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.analytics import utilization as utilization_analytics
from costlab.analytics.anomalies import detect_anomalies
from costlab.analytics.budget import list_budgets
from costlab.analytics.cost import cost_by_service, cost_summary
from costlab.analytics.forecasting import build_forecast
from costlab.analytics.freshness import compute_freshness
from costlab.analytics.savings import savings_summary
from costlab.config import Settings
from costlab.db.models import CostRecord, Resource
from costlab.schemas.cost import CostFilters
from costlab.schemas.utilization import UtilizationFilters

if TYPE_CHECKING:
    from costlab.ai.base import AdvisorContext


def build_advisor_context(session: Session, settings: Settings) -> AdvisorContext:
    from costlab.ai.base import AdvisorContext  # local import avoids a cycle

    filters = CostFilters()

    # --- cost ---
    summary = cost_summary(session, filters)
    services = cost_by_service(session, filters)[:5]
    newest = session.execute(select(func.max(CostRecord.usage_date))).scalar_one()
    fresh = compute_freshness(newest, _now(), settings.freshness_max_hours)

    cost = {
        "total_cost": summary.cost,
        "total_net_cost": summary.net_cost,
        "total_credits": summary.credits,
        "top_services": [
            {"service": row.key, "cost": row.cost, "share_pct": 0.0} for row in services
        ],
        "freshness": fresh.as_dict(),
    }

    # --- resources + utilization ---
    rows, pagination, counts, window = utilization_analytics.list_utilization(
        session, UtilizationFilters(), 1, 100
    )
    resources_all = session.query(Resource).all()
    by_type: dict[str, int] = {}
    for resource in resources_all:
        by_type[resource.resource_type] = by_type.get(resource.resource_type, 0) + 1
    resources = {
        "count": len(resources_all),
        "by_type": by_type,
        "unallocated": sum(1 for r in resources_all if r.owner is None),
    }
    low = [row.resource_id for row in rows if row.signals.low_utilization]
    high = [row.resource_id for row in rows if row.signals.high_utilization]
    unstable = [row.resource_id for row in rows if row.signals.unstable_utilization]
    utilization = {
        "window": {"start": window.start.isoformat(), "end": window.end.isoformat()}
        if window
        else None,
        "low_utilization": low,
        "high_utilization": high,
        "unstable_utilization": unstable,
        "no_cpu_data": [row.resource_id for row in rows if row.avg_cpu is None],
        "per_resource": [
            {
                "resource_id": row.resource_id,
                "resource_type": row.resource_type,
                "avg_cpu": row.avg_cpu,
                "avg_memory": row.metrics["memory_utilization"].avg
                if "memory_utilization" in row.metrics
                else None,
                "cost_in_window": row.cost_in_window,
                "requests_avg": row.metrics["request_count"].avg
                if "request_count" in row.metrics
                else None,
            }
            for row in rows
        ][:12],
    }

    # --- recommendations ---
    from costlab.db.models import Recommendation

    rec_rows = (
        session.execute(select(Recommendation).order_by(Recommendation.priority_score.desc()))
        .scalars()
        .all()
    )
    rec_context = {
        "total": len(rec_rows),
        "top": [
            {
                "id": row.id,
                "rule_id": row.rule_id,
                "title": row.title,
                "resource": row.resource_id or f"{row.project_id}/{row.service_id}",
                "priority_score": float(row.priority_score),
                "potential_savings": float(row.potential_savings),
                "risk": row.risk,
                "confidence": row.confidence,
                "status": row.status,
            }
            for row in rec_rows[:5]
        ],
    }

    # --- anomalies ---
    hits = detect_anomalies(session)
    anomalies = {
        "count": len(hits),
        "recent": [
            {
                "date": hit.date.isoformat(),
                "resource": hit.resource_name or f"{hit.project_id}/{hit.service_id}",
                "actual": hit.actual,
                "expected": hit.expected,
                "difference": hit.difference,
                "percentage_change": hit.percentage_change,
                "z_score": hit.z_score,
                "severity": hit.severity,
            }
            for hit in hits[:5]
        ],
    }

    # --- forecast ---
    forecast = build_forecast(session, filters, 30)
    forecast_context = {
        "sufficient_data": forecast["sufficient_data"],
        "trend": forecast.get("trend"),
        "confidence": forecast.get("confidence"),
        "totals": forecast.get("totals"),
    }

    # --- budget ---
    budgets = [
        {
            "name": b["name"],
            "limit": b["limit"],
            "spend": b["spend"]["amount"] if b["spend"] else None,
            "status": b["status"],
            "projected_month_end": b["projected_month_end"],
            "forecast_over_budget": b["forecast_over_budget"],
        }
        for b in list_budgets(session)
    ]

    # --- savings lifecycle ---
    savings = savings_summary(session)

    environment = {
        "demo_mode": settings.demo_mode,
        "data_source": "mock" if settings.demo_mode else "gcp",
        "freshness": fresh.as_dict(),
        "savings": savings,
    }

    return AdvisorContext(
        environment=environment,
        cost=cost,
        resources=resources,
        utilization=utilization,
        recommendations=rec_context,
        anomalies=anomalies,
        forecast=forecast_context,
        budget={"budgets": budgets},
    )


def _now() -> Any:
    from datetime import UTC, datetime

    return datetime.now(UTC)
