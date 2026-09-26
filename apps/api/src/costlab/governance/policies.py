"""Governance policies (Phase 6, CLAUDE.md §32).

Policies are ADVISORY ONLY: a violation produces a warning, evidence and
audit information — never an automated action (CLAUDE.md §34, §38; the
platform has no infrastructure-modifying capability at all).

Evaluation happens at read time against the current data. Statuses:
- PASS      — no findings;
- WARNING   — policy gap or unverifiable condition (e.g. missing labels,
              schedule not configured, cannot verify public IP);
- VIOLATION — hard breach (e.g. a resource above MAX_MONTHLY_COST).

Boundaries are strict where money is involved: a resource costing exactly
the MAX_MONTHLY_COST threshold is NOT a violation (strictly above is).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.analytics.cost import _money
from costlab.db.models import CostRecord, Policy, Resource

POLICY_DEFINITIONS: list[dict[str, Any]] = [
    {
        "policy_id": "REQUIRE_OWNER_LABEL",
        "name": "Require owner label",
        "description": "Every resource must carry an owner label so cost can be attributed. "
        "Unattributed cost is reported as UNALLOCATED, never guessed.",
        "config": {},
    },
    {
        "policy_id": "REQUIRE_ENVIRONMENT_LABEL",
        "name": "Require environment label",
        "description": "Every resource must declare development / staging / production so "
        "policies can be applied per environment.",
        "config": {},
    },
    {
        "policy_id": "MAX_MONTHLY_COST",
        "name": "Max monthly cost per resource",
        "description": "A single resource may not cost more than the configured monthly amount "
        "(trailing 30 days, gross). Strictly-above triggers; exactly at the limit passes.",
        "config": {"monthly_cost_usd": 10.0},
    },
    {
        "policy_id": "NO_PUBLIC_DATABASE",
        "name": "No public database",
        "description": "Database instances must not be publicly reachable. When the data does "
        "not record public/private IP information the policy reports WARNING "
        "(cannot verify) instead of a false PASS.",
        "config": {},
    },
    {
        "policy_id": "DEV_RESOURCE_SCHEDULE",
        "name": "Development resource schedule",
        "description": "Development compute resources should declare an off-hours schedule "
        "(e.g. 08:00-18:00 weekdays) to avoid paying for idle nights and weekends.",
        "config": {},
    },
]


@dataclass
class PolicyFinding:
    resource_id: str | None
    resource_name: str
    detail: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "detail": self.detail,
        }


@dataclass
class PolicyResult:
    policy_id: str
    name: str
    description: str
    enabled: bool
    config: dict[str, Any]
    status: str  # PASS | WARNING | VIOLATION
    summary: str
    findings: list[PolicyFinding] = field(default_factory=list)


@dataclass
class ResourceFact:
    """What policies may read about one resource (evidence boundary)."""

    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    environment: str
    owner: str | None
    labels: dict[str, Any]
    monthly_cost: float | None  # trailing 30 days, gross; None = no cost data


def _collect_resource_facts(session: Session) -> list[ResourceFact]:
    """Resources joined with their trailing-30-day gross cost (§3 convention)."""
    resources = session.execute(select(Resource).order_by(Resource.resource_id)).scalars().all()
    max_date = session.execute(select(func.max(CostRecord.usage_date))).scalar_one()
    costs: dict[str, float] = {}
    if max_date is not None:
        window_start = max_date - timedelta(days=29)
        rows = session.execute(
            select(CostRecord.resource_id, func.sum(CostRecord.cost))
            .where(CostRecord.usage_date >= window_start, CostRecord.usage_date <= max_date)
            .group_by(CostRecord.resource_id)
        ).all()
        costs = {resource_id: _money(total) for resource_id, total in rows if resource_id}
    return [
        ResourceFact(
            resource_id=r.resource_id,
            resource_name=r.resource_name,
            resource_type=r.resource_type,
            service_id=r.service_id,
            environment=r.environment,
            owner=r.owner,
            labels=r.labels or {},
            monthly_cost=costs.get(r.resource_id),
        )
        for r in resources
    ]


# --- Individual evaluators (pure given the facts; unit-testable) --------------


def evaluate_require_owner_label(facts: list[ResourceFact], config: dict[str, Any]) -> PolicyResult:
    findings = [
        PolicyFinding(
            resource_id=f.resource_id,
            resource_name=f.resource_name,
            detail="No owner label — cost is attributed as UNALLOCATED.",
        )
        for f in facts
        if f.owner is None
    ]
    status = "PASS" if not findings else "WARNING"
    summary = (
        "All resources carry an owner label."
        if not findings
        else f"{len(findings)} resource(s) missing the owner label (cost reported as UNALLOCATED)."
    )
    return PolicyResult(
        "REQUIRE_OWNER_LABEL", "Require owner label", "", True, config, status, summary, findings
    )


def evaluate_require_environment_label(
    facts: list[ResourceFact], config: dict[str, Any]
) -> PolicyResult:
    findings = [
        PolicyFinding(
            resource_id=f.resource_id,
            resource_name=f.resource_name,
            detail="No environment label on the resource.",
        )
        for f in facts
        if "environment" not in f.labels
    ]
    status = "PASS" if not findings else "WARNING"
    summary = (
        "All resources declare an environment."
        if not findings
        else f"{len(findings)} resource(s) missing the environment label."
    )
    return PolicyResult(
        "REQUIRE_ENVIRONMENT_LABEL",
        "Require environment label",
        "",
        True,
        config,
        status,
        summary,
        findings,
    )


def evaluate_max_monthly_cost(facts: list[ResourceFact], config: dict[str, Any]) -> PolicyResult:
    """Strictly-abowe triggers: exactly at the limit is compliant (boundary)."""
    limit = float(config.get("monthly_cost_usd", 10.0))
    findings = [
        PolicyFinding(
            resource_id=f.resource_id,
            resource_name=f.resource_name,
            detail=f"Trailing-30-day cost ${f.monthly_cost:.2f} exceeds the ${limit:.2f} limit "
            f"({f.monthly_cost / limit * 100:.0f}% of budget).",
        )
        for f in facts
        if f.monthly_cost is not None and f.monthly_cost > limit
    ]
    status = "PASS" if not findings else "VIOLATION"
    summary = (
        f"No resource exceeds the ${limit:.2f}/month limit."
        if not findings
        else f"{len(findings)} resource(s) above the ${limit:.2f}/month limit."
    )
    return PolicyResult(
        "MAX_MONTHLY_COST",
        "Max monthly cost per resource",
        "",
        True,
        config,
        status,
        summary,
        findings,
    )


def evaluate_no_public_database(facts: list[ResourceFact], config: dict[str, Any]) -> PolicyResult:
    """Public/private reachability must come from data. When the data does not
    record it, the result is WARNING (cannot verify) — never a false PASS."""
    findings: list[PolicyFinding] = []
    violations = 0
    unverifiable = 0
    for f in facts:
        if f.resource_type != "sql_instance":
            continue
        public = f.labels.get("public_ip")
        if public is True or (isinstance(public, str) and public.lower() == "true"):
            violations += 1
            findings.append(
                PolicyFinding(
                    resource_id=f.resource_id,
                    resource_name=f.resource_name,
                    detail="Database reports public_ip=true — publicly reachable.",
                )
            )
        elif public is None:
            unverifiable += 1
            findings.append(
                PolicyFinding(
                    resource_id=f.resource_id,
                    resource_name=f.resource_name,
                    detail="No public/private IP information in the data — cannot verify; "
                    "manual review required.",
                )
            )
    if violations:
        status, summary = (
            "VIOLATION",
            f"{violations} database(s) publicly reachable"
            + (f", {unverifiable} unverifiable." if unverifiable else "."),
        )
    elif unverifiable:
        status, summary = (
            "WARNING",
            f"{unverifiable} database(s) lack reachability data — cannot verify.",
        )
    else:
        status, summary = "PASS", "All databases verified private."
    return PolicyResult(
        "NO_PUBLIC_DATABASE", "No public database", "", True, config, status, summary, findings
    )


def evaluate_dev_resource_schedule(
    facts: list[ResourceFact], config: dict[str, Any]
) -> PolicyResult:
    """Development compute without a declared schedule — a §31 scheduling gap."""
    findings = [
        PolicyFinding(
            resource_id=f.resource_id,
            resource_name=f.resource_name,
            detail="Development resource without a schedule label — consider "
            "off-hours shutdown (e.g. 08:00-18:00 weekdays).",
        )
        for f in facts
        if f.environment == "development"
        and f.resource_type in ("vm_instance", "sql_instance")
        and not f.labels.get("schedule")
    ]
    status = "PASS" if not findings else "WARNING"
    summary = (
        "All development resources declare a schedule."
        if not findings
        else f"{len(findings)} development resource(s) without an off-hours schedule."
    )
    return PolicyResult(
        "DEV_RESOURCE_SCHEDULE",
        "Development resource schedule",
        "",
        True,
        config,
        status,
        summary,
        findings,
    )


_EVALUATORS = {
    "REQUIRE_OWNER_LABEL": evaluate_require_owner_label,
    "REQUIRE_ENVIRONMENT_LABEL": evaluate_require_environment_label,
    "MAX_MONTHLY_COST": evaluate_max_monthly_cost,
    "NO_PUBLIC_DATABASE": evaluate_no_public_database,
    "DEV_RESOURCE_SCHEDULE": evaluate_dev_resource_schedule,
}


def evaluate_policies(session: Session) -> list[PolicyResult]:
    """Evaluate every enabled policy definition against the current data."""
    facts = _collect_resource_facts(session)
    definitions = session.execute(select(Policy).order_by(Policy.id)).scalars().all()
    results: list[PolicyResult] = []
    for policy in definitions:
        evaluator = _EVALUATORS.get(policy.policy_id)
        if evaluator is None or not policy.enabled:
            continue
        result = evaluator(facts, policy.config or {})
        result.description = policy.description
        result.enabled = policy.enabled
        results.append(result)
    return results


def ensure_default_policies(session: Session) -> None:
    """Idempotently create the policy definitions (config from code)."""
    existing = {row[0] for row in session.execute(select(Policy.policy_id)).all()}
    for definition in POLICY_DEFINITIONS:
        if definition["policy_id"] in existing:
            continue
        session.add(
            Policy(
                policy_id=definition["policy_id"],
                name=definition["name"],
                description=definition["description"],
                config=definition["config"],
            )
        )
    session.flush()
