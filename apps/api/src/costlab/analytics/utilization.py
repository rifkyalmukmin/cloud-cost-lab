"""Resource utilization analytics (Phase 4).

EVIDENCE ONLY, no recommendations: this module quantifies how utilized each
resource is (avg / min / max / P95 / stddev per metric) over a data-anchored
window and flags heuristic signals (low / high / unstable / missing metrics).
The recommendation engine (later phase) is the consumer of this evidence.

Rules carried over from the cost analytics (CLAUDE.md §9, §14, §41):
- aggregation happens in SQL (one grouped query), never row-by-row in Python;
- the default window comes from the data itself (min/max usage_date), never
  the wall clock;
- a metric observed as 0 is a real zero and is kept; a metric with NO samples
  in the window is missing and is listed in `missing_metrics`, never 0;
- cost linkage uses cost records inside the SAME window as the stats, so the
  Cost-vs-Utilization view compares like with like.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, Subquery, func, select
from sqlalchemy.orm import Session

from costlab.analytics.cost import _money
from costlab.db.models import CostRecord, Project, Resource, ResourceUsage, Service
from costlab.schemas.cost import PaginationOut, PeriodOut
from costlab.schemas.resources import UtilizationPoint
from costlab.schemas.utilization import (
    EvidenceSignals,
    MetricStats,
    SignalCounts,
    UtilizationFilters,
)

# Metrics exposed by the utilization endpoints, in reporting order.
METRIC_COLUMNS: dict[str, Any] = {
    "cpu_utilization": ResourceUsage.cpu_utilization,
    "memory_utilization": ResourceUsage.memory_utilization,
    "disk_utilization": ResourceUsage.disk_utilization,
    "network_in_mb": ResourceUsage.network_in_mb,
    "network_out_mb": ResourceUsage.network_out_mb,
    "connections": ResourceUsage.connections,
    "request_count": ResourceUsage.request_count,
    "latency_ms": ResourceUsage.latency_ms,
    "error_rate_pct": ResourceUsage.error_rate_pct,
}

# --- Evidence thresholds (project-specific heuristics, NOT standards) --------
# LOW aligns with the rightsizing evidence rule (CLAUDE.md §17: CPU < 20%).
LOW_CPU_AVG = 20.0  # percent
HIGH_CPU_AVG = 80.0  # percent
# A day-to-day stddev above this means the workload swings too much to call
# its average representative.
UNSTABLE_CPU_STDDEV = 15.0  # percentage points
# Stability needs at least a week of samples to mean anything.
MIN_SAMPLES_FOR_UNSTABLE = 7


@dataclass(frozen=True)
class UtilizationRow:
    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    service_name: str
    project_id: str
    project_name: str
    environment: str
    region: str
    machine_type: str | None
    window: PeriodOut
    metrics: dict[str, MetricStats]
    missing_metrics: list[str]
    cost_in_window: float | None
    cost_credits_in_window: float | None
    cost_net_in_window: float | None
    signals: EvidenceSignals

    @property
    def avg_cpu(self) -> float | None:
        cpu = self.metrics.get("cpu_utilization")
        return cpu.avg if cpu else None


def _r(value: Any, digits: int = 2) -> float | None:
    return round(float(value), digits) if value is not None else None


def get_window(session: Session, filters: UtilizationFilters) -> PeriodOut | None:
    """Effective window, anchored to the utilization data (not the wall clock)."""
    row = session.execute(
        select(
            func.min(ResourceUsage.usage_date).label("min_date"),
            func.max(ResourceUsage.usage_date).label("max_date"),
        )
    ).one()
    if row.min_date is None or row.max_date is None:
        return None
    return PeriodOut(
        start=filters.start_date or row.min_date,
        end=filters.end_date or row.max_date,
    )


def apply_filters(stmt: Select[Any], filters: UtilizationFilters) -> Select[Any]:
    """Dimension filters on the outer query (the date window lives inside the
    aggregate subqueries, where it cannot fan out the joined rows)."""
    if filters.project_id:
        stmt = stmt.where(Resource.project_id == filters.project_id)
    if filters.service:
        stmt = stmt.where(Resource.service_id == filters.service)
    if filters.environment:
        stmt = stmt.where(Resource.environment == filters.environment)
    return stmt


def classify_signals(cpu: MetricStats | None) -> EvidenceSignals:
    """Heuristic evidence flags from CPU stats. Null when CPU is missing."""
    if cpu is None:
        return EvidenceSignals()
    return EvidenceSignals(
        low_utilization=cpu.avg < LOW_CPU_AVG,
        high_utilization=cpu.avg > HIGH_CPU_AVG,
        unstable_utilization=(
            cpu.stddev is not None
            and cpu.sample_count >= MIN_SAMPLES_FOR_UNSTABLE
            and cpu.stddev > UNSTABLE_CPU_STDDEV
        ),
    )


def _aggregate_expression(metric: str) -> dict[str, Any]:
    """One metric's aggregate expressions, labelled `<metric>_<stat>`.

    Order matters: `_METRIC_OFFSETS` maps each metric to its position in the
    result row (count, avg, min, max, stddev, p95) because the row is read
    positionally — the same convention as the cost/resource analytics.
    """
    col = METRIC_COLUMNS[metric]
    return {
        f"{metric}_count": func.count(col),
        f"{metric}_avg": func.avg(col),
        f"{metric}_min": func.min(col),
        f"{metric}_max": func.max(col),
        f"{metric}_stddev": func.stddev_samp(col),
        f"{metric}_p95": func.percentile_cont(0.95).within_group(col.asc()),
    }


# Position of each metric's first aggregate (count) in the result row:
# [0]=Resource, [1]=service name, [2]=project name, [3..5]=cost sums, then 6
# aggregates per metric in METRIC_COLUMNS order.
_STATS_PER_METRIC = 6
_STAT_NAMES = ("count", "avg", "min", "max", "stddev", "p95")
_METRIC_OFFSETS = {
    metric: 6 + index * _STATS_PER_METRIC for index, metric in enumerate(METRIC_COLUMNS)
}


def _usage_stats_subquery(window: PeriodOut) -> Subquery:
    """Per-resource metric aggregates over the window.

    Aggregating usage in its own grouped subquery (before any join to cost)
    is essential: a resource can have several cost records per day (multiple
    SKUs), so joining cost first would fan out usage rows and corrupt every
    count, average and P95.
    """
    stmt: Select[Any] = select(ResourceUsage.resource_id)
    for metric in METRIC_COLUMNS:
        for label, expression in _aggregate_expression(metric).items():
            stmt = stmt.add_columns(expression.label(label))
    return (
        stmt.where(
            ResourceUsage.usage_date >= window.start,
            ResourceUsage.usage_date <= window.end,
        )
        .group_by(ResourceUsage.resource_id)
        .subquery()
    )


def _cost_subquery(window: PeriodOut) -> Subquery:
    """Per-resource cost summed over the same window (same trick as the
    resource inventory's monthly cost)."""
    return (
        select(
            CostRecord.resource_id,
            func.sum(CostRecord.cost).label("cost_in_window"),
            func.sum(CostRecord.credits).label("cost_credits_in_window"),
            func.sum(CostRecord.net_cost).label("cost_net_in_window"),
        )
        .where(
            CostRecord.usage_date >= window.start,
            CostRecord.usage_date <= window.end,
        )
        .group_by(CostRecord.resource_id)
        .subquery()
    )


def _base_query(window: PeriodOut) -> Select[Any]:
    """Resource identity + usage stats + cost, one row per resource."""
    usage = _usage_stats_subquery(window)
    cost = _cost_subquery(window)
    stmt: Select[Any] = select(
        Resource,
        Service.display_name,
        Project.display_name,
        cost.c.cost_in_window,
        cost.c.cost_credits_in_window,
        cost.c.cost_net_in_window,
    )
    for metric in METRIC_COLUMNS:
        for stat in _STAT_NAMES:
            stmt = stmt.add_columns(usage.c[f"{metric}_{stat}"])
    stmt = (
        stmt.join(Service, Resource.service_id == Service.id)
        .join(Project, Resource.project_id == Project.id)
        .outerjoin(usage, Resource.resource_id == usage.c.resource_id)
        .outerjoin(cost, Resource.resource_id == cost.c.resource_id)
    )
    return stmt


def _metric_stats(row: Any, metric: str) -> MetricStats | None:
    base = _METRIC_OFFSETS[metric]
    count = row[base]
    if not count:
        return None
    avg = row[base + 1]
    minimum = row[base + 2]
    maximum = row[base + 3]
    stddev = row[base + 4]
    p95 = row[base + 5]
    if avg is None or minimum is None or maximum is None or p95 is None:
        # Defensive: Postgres never returns this combination when count > 0.
        return None
    return MetricStats(
        avg=round(float(avg), 2),
        min=round(float(minimum), 2),
        max=round(float(maximum), 2),
        p95=round(float(p95), 2),
        stddev=_r(stddev),
        sample_count=int(count),
    )


def _build_row(
    window: PeriodOut,
    resource: Resource,
    service_name: str,
    project_name: str,
    aggregates: Any,
    cost: tuple[Any, Any, Any] | None,
) -> UtilizationRow:
    metrics: dict[str, MetricStats] = {}
    missing: list[str] = []
    for metric in METRIC_COLUMNS:
        stats = _metric_stats(aggregates, metric)
        if stats is None:
            missing.append(metric)
        else:
            metrics[metric] = stats
    cost_values = cost if cost is not None else (None, None, None)
    return UtilizationRow(
        resource_id=resource.resource_id,
        resource_name=resource.resource_name,
        resource_type=resource.resource_type,
        service_id=resource.service_id,
        service_name=service_name,
        project_id=resource.project_id,
        project_name=project_name,
        environment=resource.environment,
        region=resource.region,
        machine_type=resource.machine_type,
        window=window,
        metrics=metrics,
        missing_metrics=missing,
        cost_in_window=_money(cost_values[0]) if cost_values[0] is not None else None,
        cost_credits_in_window=_money(cost_values[1]) if cost_values[1] is not None else None,
        cost_net_in_window=_money(cost_values[2]) if cost_values[2] is not None else None,
        signals=classify_signals(metrics.get("cpu_utilization")),
    )


def _sorted_rows(rows: list[UtilizationRow]) -> list[UtilizationRow]:
    """Most utilized first (avg_cpu DESC, nulls last), then by resource id."""
    rows.sort(key=lambda row: row.resource_id)  # stable tie-break
    rows.sort(
        key=lambda row: (row.avg_cpu is not None, row.avg_cpu or 0.0),
        reverse=True,
    )
    return rows


def signal_counts(rows: list[UtilizationRow]) -> SignalCounts:
    return SignalCounts(
        low_utilization=sum(1 for r in rows if r.signals.low_utilization),
        high_utilization=sum(1 for r in rows if r.signals.high_utilization),
        unstable_utilization=sum(1 for r in rows if r.signals.unstable_utilization),
        missing_cpu=sum(1 for r in rows if "cpu_utilization" in r.missing_metrics),
    )


def list_utilization(
    session: Session,
    filters: UtilizationFilters,
    page: int,
    page_size: int,
) -> tuple[list[UtilizationRow], PaginationOut, SignalCounts, PeriodOut | None]:
    """Per-resource stats for the filtered set.

    The aggregate returns one row per resource (bounded by the resource
    dimension, not the days dimension), so the page slice happens on the
    already-computed rows and signal counts cover the full filtered set.
    """
    window = get_window(session, filters)
    if window is None:
        empty = PaginationOut(page=page, page_size=page_size, total_items=0, total_pages=0)
        no_signals = SignalCounts(
            low_utilization=0, high_utilization=0, unstable_utilization=0, missing_cpu=0
        )
        return [], empty, no_signals, None

    stmt = apply_filters(_base_query(window), filters).order_by(Resource.resource_id.asc())
    rows: list[UtilizationRow] = []
    for result in session.execute(stmt):
        resource = result[0]
        rows.append(
            _build_row(
                window=window,
                resource=resource,
                service_name=result[1],
                project_name=result[2],
                aggregates=result,
                cost=(result[3], result[4], result[5]),
            )
        )
    rows = _sorted_rows(rows)
    counts = signal_counts(rows)
    start = (page - 1) * page_size
    pagination = PaginationOut(
        page=page,
        page_size=page_size,
        total_items=len(rows),
        total_pages=(len(rows) + page_size - 1) // page_size,
    )
    return rows[start : start + page_size], pagination, counts, window


def get_utilization_detail(
    session: Session,
    resource_id: str,
    filters: UtilizationFilters,
) -> UtilizationRow | None:
    """Stats + series for one resource, or None when the id is unknown.

    A resource that exists but has no usage samples in the window still
    returns a row: its metrics are then all missing (NULL aggregates via the
    outer join) — missing data, not a missing resource.
    """
    window = get_window(session, filters)
    if window is None:
        return None
    resource = session.get(Resource, resource_id)
    if resource is None:
        return None

    stmt = _base_query(window).where(Resource.resource_id == resource_id)
    result = session.execute(stmt).one_or_none()
    if result is None:
        return None
    return _build_row(
        window=window,
        resource=result[0],
        service_name=result[1],
        project_name=result[2],
        aggregates=result,
        cost=(result[3], result[4], result[5]),
    )


def _related_name(session: Session, model: type[Any], key: str) -> str:
    """Display name of a related row, falling back to the raw key."""
    related = session.get(model, key)
    return related.display_name if related else key


def get_utilization_series(
    session: Session,
    resource_id: str,
    window: PeriodOut,
) -> list[UtilizationPoint]:
    """Daily samples within the window, date ascending."""
    rows = (
        session.execute(
            select(ResourceUsage)
            .where(
                ResourceUsage.resource_id == resource_id,
                ResourceUsage.usage_date >= window.start,
                ResourceUsage.usage_date <= window.end,
            )
            .order_by(ResourceUsage.usage_date.asc())
        )
        .scalars()
        .all()
    )
    return [
        UtilizationPoint(
            date=row.usage_date,
            cpu_utilization=_r(row.cpu_utilization),
            memory_utilization=_r(row.memory_utilization),
            disk_utilization=_r(row.disk_utilization),
            network_in_mb=_r(row.network_in_mb),
            network_out_mb=_r(row.network_out_mb),
            connections=row.connections,
            request_count=row.request_count,
            error_rate_pct=_r(row.error_rate_pct, digits=3),
        )
        for row in rows
    ]


def expected_p95(values: list[Decimal | float]) -> float:
    """Linear-interpolation P95 — mirrors SQL percentile_cont (test helper)."""
    ordered = sorted(float(v) for v in values)
    if not ordered:
        raise ValueError("P95 of an empty sample set is undefined")
    if len(ordered) == 1:
        return ordered[0]
    rank = 0.95 * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return round(ordered[lower] + fraction * (ordered[upper] - ordered[lower]), 2)
