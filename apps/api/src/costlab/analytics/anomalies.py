"""Cost anomaly detection (Phase 7, CLAUDE.md §28).

Two one-sided detectors on daily net cost per (project, service, resource):

- **rolling average** — expected cost = mean of the previous BASELINE_DAYS
  available days (gaps are simply missing days, not zeros);
- **z-score** — how many baseline standard deviations the day sits above that
  expected level.

A day is an anomaly when ALL of the following hold (noise floor philosophy,
same as the Phase 5 rule):
- it is an INCREASE (actual > expected) — decreases are not "unexpected cost";
- z >= min_z_score (default 2.0);
- percentage_change >= 25%;
- difference >= $0.05 (absolute floor — suppresses noise on tiny bills).

Perfectly flat baselines (stddev == 0) make the z-score undefined; such
step-changes are still surfaced through the percentage path with severity LOW
and confidence LOW — never silently dropped, never fabricated z values.

Severity: HIGH when z >= 4 or change >= 100%; MEDIUM when z >= 3 or
change >= 60%; LOW otherwise. Confidence reflects evidence quality (baseline
sample count, z strength).

Relationship to Phase 5: the recommendation engine's CostAnomalyRule groups
consecutive spike days into run-level findings for the approval workflow;
this module exposes the underlying point-level detections (per day) via
`GET /api/anomalies`.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.analytics.cost import _money, get_bounds
from costlab.db.models import CostRecord, Project, Resource, Service

BASELINE_DAYS = 14
DEFAULT_MIN_Z = 2.0
MIN_PCT_CHANGE = 25.0
MIN_DIFFERENCE_USD = 0.05


@dataclass(frozen=True)
class AnomalyHit:
    date: date
    project_id: str
    project_name: str
    service_id: str
    service_name: str
    resource_id: str | None
    resource_name: str | None
    actual: float
    expected: float
    difference: float
    percentage_change: float
    z_score: float | None  # None when the baseline stddev is zero
    severity: str
    confidence: str
    baseline_samples: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "project_id": self.project_id,
            "project_name": self.project_name,
            "service_id": self.service_id,
            "service_name": self.service_name,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "actual": self.actual,
            "expected": self.expected,
            "difference": self.difference,
            "percentage_change": self.percentage_change,
            "z_score": self.z_score,
            "severity": self.severity,
            "confidence": self.confidence,
            "baseline_samples": self.baseline_samples,
        }


def _classify(z: float | None, pct: float, samples: int) -> tuple[str, str]:
    if z is not None:
        if z >= 4.0 or pct >= 100:
            severity = "HIGH"
        elif z >= 3.0 or pct >= 60:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        if samples >= 10 and z >= 3:
            confidence = "HIGH"
        elif samples >= 7:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
    else:
        # Flat baseline step-change: real but weakly evidenced.
        severity, confidence = "LOW", "LOW"
    return severity, confidence


def _load_names(session: Session) -> dict[str, dict[str, str]]:
    """Display names for projects, services and resources."""
    return {
        "projects": {
            pid: name
            for pid, name in session.execute(select(Project.id, Project.display_name)).all()
        },
        "services": {
            sid: name
            for sid, name in session.execute(select(Service.id, Service.display_name)).all()
        },
        "resources": {
            rid: name
            for rid, name in session.execute(
                select(Resource.resource_id, Resource.resource_name)
            ).all()
        },
    }


def _load_series(
    session: Session,
) -> dict[tuple[str, str, str | None], list[tuple[date, float]]]:
    """Daily net-cost series per (project, service, resource); missing days
    stay missing (gaps are not zeros)."""
    bounds = get_bounds(session)
    if bounds is None:
        return {}
    rows = session.execute(
        select(
            CostRecord.project_id,
            CostRecord.service_id,
            CostRecord.resource_id,
            CostRecord.usage_date,
            func.sum(CostRecord.net_cost),
        )
        .where(CostRecord.usage_date >= bounds.min_date, CostRecord.usage_date <= bounds.max_date)
        .group_by(
            CostRecord.project_id,
            CostRecord.service_id,
            CostRecord.resource_id,
            CostRecord.usage_date,
        )
        .order_by(CostRecord.usage_date.asc())
    ).all()
    series: dict[tuple[str, str, str | None], list[tuple[date, float]]] = {}
    for project_id, service_id, resource_id, day, total in rows:
        series.setdefault((project_id, service_id, resource_id), []).append((day, _money(total)))
    return series


def detect_anomalies(
    session: Session,
    *,
    min_z_score: float = DEFAULT_MIN_Z,
) -> list[AnomalyHit]:
    """Scan every (project, service, resource) daily series for increases."""
    series = _load_series(session)
    names = _load_names(session)

    hits: list[AnomalyHit] = []
    for (project_id, service_id, resource_id), points in series.items():
        if len(points) <= BASELINE_DAYS:
            continue  # no baseline yet — never flag the warm-up period
        for index in range(BASELINE_DAYS, len(points)):
            day, actual = points[index]
            baseline = [value for _, value in points[index - BASELINE_DAYS : index]]
            expected = sum(baseline) / len(baseline)
            difference = actual - expected
            if difference < MIN_DIFFERENCE_USD or expected <= 0:
                continue  # noise floor / decrease / zero baseline
            pct = difference / expected * 100
            if pct < MIN_PCT_CHANGE:
                continue
            stddev = statistics.stdev(baseline) if len(baseline) > 1 else 0.0
            z: float | None = round((actual - expected) / stddev, 2) if stddev > 0 else None
            if z is not None and z < min_z_score:
                continue
            severity, confidence = _classify(z, pct, len(baseline))
            hits.append(
                AnomalyHit(
                    date=day,
                    project_id=project_id,
                    project_name=names["projects"].get(project_id, project_id),
                    service_id=service_id,
                    service_name=names["services"].get(service_id, service_id),
                    resource_id=resource_id,
                    resource_name=(
                        names["resources"].get(resource_id, resource_id) if resource_id else None
                    ),
                    actual=round(actual, 4),
                    expected=round(expected, 4),
                    difference=round(difference, 4),
                    percentage_change=round(pct, 1),
                    z_score=z,
                    severity=severity,
                    confidence=confidence,
                    baseline_samples=len(baseline),
                )
            )

    hits.sort(key=lambda hit: (-hit.date.toordinal(), -(hit.z_score or 0.0)))
    return hits
