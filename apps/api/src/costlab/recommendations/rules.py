"""The five Phase 5 recommendation rules.

Every rule implements `RecommendationRule` (evaluate / explain /
calculate_saving / calculate_risk / confidence) and refuses to emit a
recommendation when the evidence is missing, ambiguous, or on the wrong
side of a threshold boundary — false positives are worse than silence.

Thresholds are project-specific heuristics (CLAUDE.md §16-§19, §24, §28),
documented in docs/recommendation-engine.md — not industry standards.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from costlab.analytics.utilization import UtilizationRow
from costlab.db.models import CostRecord, Resource
from costlab.recommendations.base import (
    Evidence,
    RecommendationDraft,
    RecommendationRule,
    money,
)

# --- IdleComputeRule (CLAUDE.md §16) -----------------------------------------
IDLE_CPU_AVG_MAX = 5.0  # percent, strictly below
IDLE_CPU_P95_MAX = 20.0  # burst guard: a low average with high P95 is NOT idle
IDLE_NETWORK_MB_MAX = 100.0  # combined avg in+out MB/day, strictly below
IDLE_MIN_SAMPLES = 7  # at least a week of daily samples
IDLE_SCHEDULE_FACTOR = 0.6  # dev VMs: ~10h/day on => ~60% of the bill saved

# --- OversizedComputeRule (CLAUDE.md §17) ------------------------------------
OVERSIZED_CPU_AVG_MAX = 20.0  # percent, strictly below
OVERSIZED_MEM_AVG_MAX = 40.0  # percent, strictly below
OVERSIZED_CPU_P95_MAX = 40.0  # headroom must survive the resize
OVERSIZED_STDDEV_MAX = 15.0  # workload must be stable enough to trust the mean
OVERSIZED_MIN_SAMPLES = 14
# Same-family one-step-down map; ratio ≈ listed-price share of the smaller
# shape (documented approximation, not a quote).
MACHINE_STEP_DOWN = {
    "e2-standard-4": "e2-standard-2",
    "e2-standard-2": "e2-small",
    "e2-medium": "e2-small",
    "e2-small": "e2-micro",
}
RESIZE_COST_RATIO = 0.5

# --- StorageRetentionRule (CLAUDE.md §18) ------------------------------------
STORAGE_REQUESTS_PER_DAY_MAX = 10.0  # avg, strictly below => effectively unused
STORAGE_ARCHIVE_FACTOR = 0.2  # archive-class storage ≈ 20% of standard price
STORAGE_MIN_SAMPLES = 14

# --- CostAnomalyRule (CLAUDE.md §28, phase 1: rolling average + threshold) ---
ANOMALY_BASELINE_DAYS = 14
ANOMALY_RATIO = 1.3  # day > baseline * 1.3 (strictly)
ANOMALY_MIN_DAY_DELTA = 0.05  # USD/day — suppresses noise on tiny bills
ANOMALY_MIN_RUN_DAYS = 3  # an incident, not a one-day blip
ANOMALY_MIN_EXCESS = 0.50  # USD total over the run — meaningful for this lab

# --- UnusedDiskRule (CLAUDE.md §18) ------------------------------------------
DISK_TYPES = ("disk", "persistent_disk")
DISK_USD_PER_GB_MONTH = 0.04  # pd-balanced list-price approximation


def _fmt(value: float, unit: str = "%") -> str:
    return f"{value:.1f}{unit}" if unit == "%" else f"{value:.2f} {unit}"


def _rows_by_id(context: Any) -> dict[str, UtilizationRow]:
    return {row.resource_id: row for row in context.utilization_rows}


class IdleComputeRule(RecommendationRule):
    """Avg CPU < 5% with minimal network, stable for >= 7 days (§16).

    The burst guard matters: a VM whose P95 CPU is high is NOT confidently
    idle even with a low average (periodic batches). Without CPU samples the
    rule stays silent — never guesses.
    """

    rule_id = "idle_compute"
    title = "Idle compute resource"

    def evaluate(self, session: Session, context: Any) -> list[RecommendationDraft]:
        drafts: list[RecommendationDraft] = []
        for row in context.utilization_rows:
            if row.resource_type != "vm_instance":
                continue
            cpu = row.metrics.get("cpu_utilization")
            if cpu is None:
                continue  # no CPU evidence — silence, not a guess
            net_in = row.metrics.get("network_in_mb")
            net_out = row.metrics.get("network_out_mb")
            net_avg = (
                (net_in.avg + net_out.avg) if net_in is not None and net_out is not None else None
            )
            evidence = [
                Evidence(
                    f"average CPU {_fmt(cpu.avg)} over {cpu.sample_count} days "
                    f"({row.window.start}..{row.window.end}) — below the "
                    f"{_fmt(IDLE_CPU_AVG_MAX)} idle threshold",
                    metric="cpu_utilization.avg",
                    value=cpu.avg,
                    threshold=IDLE_CPU_AVG_MAX,
                ),
                Evidence(
                    f"P95 CPU {_fmt(cpu.p95)} — no usage bursts detected "
                    f"(burst guard: <= {_fmt(IDLE_CPU_P95_MAX)})",
                    metric="cpu_utilization.p95",
                    value=cpu.p95,
                    threshold=IDLE_CPU_P95_MAX,
                ),
            ]
            if cpu.avg >= IDLE_CPU_AVG_MAX or cpu.p95 > IDLE_CPU_P95_MAX:
                continue
            if cpu.sample_count < IDLE_MIN_SAMPLES:
                continue
            if net_avg is not None:
                evidence.append(
                    Evidence(
                        f"network activity averages {_fmt(net_avg, 'MB/day')} (in+out combined), "
                        f"below the minimal-traffic threshold of {IDLE_NETWORK_MB_MAX:.0f} MB/day",
                        metric="network_mb_per_day.avg",
                        value=round(net_avg, 2),
                        threshold=IDLE_NETWORK_MB_MAX,
                    )
                )
                if net_avg >= IDLE_NETWORK_MB_MAX:
                    continue
            if row.cost_in_window is None or row.cost_in_window <= 0:
                continue  # no cost evidence — nothing to save
            evidence.append(
                Evidence(
                    f"cost in the analysis window is ${row.cost_in_window:.2f} "
                    f"({row.environment} environment)",
                    metric="cost_in_window",
                    value=row.cost_in_window,
                    unit="USD",
                )
            )
            drafts.append(
                self.build_draft(
                    evidence,
                    resource_id=row.resource_id,
                    resource_label=row.resource_name,
                    project_id=row.project_id,
                    service_id=row.service_id,
                    scope_key=row.resource_id,
                    problem=(
                        f"{row.resource_name} runs with an average CPU of {_fmt(cpu.avg)} and "
                        f"minimal network traffic for {cpu.sample_count} days — paying "
                        f"${row.cost_in_window:.2f} for a resource that appears unused."
                    ),
                    recommendation=(
                        (
                            f"Verify with the owner, then stop or decommission "
                            f"{row.resource_name}. Do not delete without human confirmation."
                            if row.environment != "development"
                            else (
                                f"Schedule {row.resource_name} off-hours "
                                "(e.g. 08:00-18:00 weekdays) or decommission it "
                                "after owner confirmation. Development resources are "
                                "safe scheduling candidates."
                            )
                        )
                        + " No automated action is taken by this platform."
                    ),
                    window_start=row.window.start,
                    window_end=row.window.end,
                    effort="LOW" if row.environment == "development" else "MEDIUM",
                )
            )
        return drafts

    def explain(self, evidence: list[Evidence]) -> str:
        return (
            "The resource shows sustained near-zero CPU, no usage bursts (P95 guard) and "
            "minimal network traffic for at least a week, while still accruing cost. "
            + " ".join(item.statement for item in evidence)
        )

    def calculate_saving(self, evidence: list[Evidence]) -> tuple[float, float, float]:
        cost = next((e.value for e in evidence if e.metric == "cost_in_window"), None)
        if cost is None or cost <= 0:
            return (0.0, 0.0, 0.0)
        is_dev = any("development environment" in e.statement for e in evidence)
        factor = IDLE_SCHEDULE_FACTOR if is_dev else 1.0
        savings = cost * factor
        return (cost, cost - savings, savings)

    def calculate_risk(self, evidence: list[Evidence]) -> str:
        return (
            "LOW" if any("development environment" in e.statement for e in evidence) else "MEDIUM"
        )

    def confidence(self, evidence: list[Evidence]) -> str:
        has_net = any(e.metric == "network_mb_per_day.avg" for e in evidence)
        return "HIGH" if has_net else "MEDIUM"


class OversizedComputeRule(RecommendationRule):
    """CPU < 20% AND memory < 40% AND stable (§17) — propose a smaller shape.

    Skips VMs already covered by the idle rule (suppressed_by), Cloud SQL
    (its rightsizing is deliberately cautious and arrives later), and any
    VM without a known machine type — no size change is proposed blind.
    """

    rule_id = "oversized_compute"
    title = "Oversized compute resource"

    def evaluate(self, session: Session, context: Any) -> list[RecommendationDraft]:
        drafts: list[RecommendationDraft] = []
        for row in context.utilization_rows:
            if row.resource_type != "vm_instance":
                continue
            current_type = row.machine_type
            if not current_type or current_type not in MACHINE_STEP_DOWN:
                continue  # unknown shape — refuse to propose a blind resize
            cpu = row.metrics.get("cpu_utilization")
            mem = row.metrics.get("memory_utilization")
            if cpu is None or mem is None:
                continue
            if cpu.sample_count < OVERSIZED_MIN_SAMPLES or mem.sample_count < OVERSIZED_MIN_SAMPLES:
                continue
            if cpu.avg >= OVERSIZED_CPU_AVG_MAX or mem.avg >= OVERSIZED_MEM_AVG_MAX:
                continue
            if cpu.p95 > OVERSIZED_CPU_P95_MAX:
                continue  # spikes would not survive a smaller shape
            if cpu.stddev is None or cpu.stddev > OVERSIZED_STDDEV_MAX:
                continue
            if row.cost_in_window is None or row.cost_in_window <= 0:
                continue
            proposed = MACHINE_STEP_DOWN[current_type]
            evidence = [
                Evidence(
                    f"average CPU {_fmt(cpu.avg)} and memory {_fmt(mem.avg)} over "
                    f"{cpu.sample_count} days — below the {_fmt(OVERSIZED_CPU_AVG_MAX)} / "
                    f"{_fmt(OVERSIZED_MEM_AVG_MAX)} oversized thresholds",
                    metric="cpu_utilization.avg",
                    value=cpu.avg,
                    threshold=OVERSIZED_CPU_AVG_MAX,
                ),
                Evidence(
                    f"P95 CPU {_fmt(cpu.p95)} leaves headroom after a resize "
                    f"(guard: <= {_fmt(OVERSIZED_CPU_P95_MAX)})",
                    metric="cpu_utilization.p95",
                    value=cpu.p95,
                    threshold=OVERSIZED_CPU_P95_MAX,
                ),
                Evidence(
                    f"CPU stddev {cpu.stddev:.1f} points — stable workload "
                    f"(guard: <= {OVERSIZED_STDDEV_MAX:.0f})",
                    metric="cpu_utilization.stddev",
                    value=cpu.stddev,
                    threshold=OVERSIZED_STDDEV_MAX,
                ),
                Evidence(
                    f"current machine type {current_type} with ${row.cost_in_window:.2f} "
                    f"cost in the window ({row.environment} environment)",
                    metric="cost_in_window",
                    value=row.cost_in_window,
                    unit="USD",
                ),
            ]
            drafts.append(
                self.build_draft(
                    evidence,
                    resource_id=row.resource_id,
                    resource_label=row.resource_name,
                    project_id=row.project_id,
                    service_id=row.service_id,
                    scope_key=row.resource_id,
                    problem=(
                        f"{row.resource_name} runs {current_type} but averages "
                        f"{_fmt(cpu.avg)} CPU / {_fmt(mem.avg)} memory — paying full price "
                        f"for capacity it does not use."
                    ),
                    recommendation=(
                        f"Migrate {row.resource_name} from {current_type} to {proposed} after a "
                        "review window. This is a SIMULATION-grade estimate — validate "
                        "performance on one instance first; production is not downsized "
                        "automatically."
                    ),
                    window_start=row.window.start,
                    window_end=row.window.end,
                    effort="MEDIUM",
                    suppressed_by=["idle_compute"],
                )
            )
        return drafts

    def explain(self, evidence: list[Evidence]) -> str:
        return (
            "Sustained low CPU AND low memory with a stable workload and P95 headroom "
            "indicate the instance shape is larger than the workload needs. "
            + " ".join(item.statement for item in evidence)
        )

    def calculate_saving(self, evidence: list[Evidence]) -> tuple[float, float, float]:
        cost = next((e.value for e in evidence if e.metric == "cost_in_window"), None)
        if cost is None or cost <= 0:
            return (0.0, 0.0, 0.0)
        savings = cost * (1 - RESIZE_COST_RATIO)
        return (cost, cost - savings, savings)

    def calculate_risk(self, evidence: list[Evidence]) -> str:
        # Production downsizing can hurt latency under load; lab-scale rule.
        return "MEDIUM" if any("production" in e.statement for e in evidence) else "LOW"

    def confidence(self, evidence: list[Evidence]) -> str:
        stddev = next((e.value for e in evidence if e.metric == "cpu_utilization.stddev"), None)
        if stddev is None:
            return "LOW"
        return "HIGH" if stddev <= OVERSIZED_STDDEV_MAX / 3 else "MEDIUM"


class UnusedDiskRule(RecommendationRule):
    """Unattached persistent disks (§18) — deleting them saves their full cost.

    Evidence required: the disk resource exists AND reports a detached state.
    The mock dataset contains no disk resources, so this rule stays silent
    there by design (documented, tested with a synthetic detached disk).
    """

    rule_id = "unused_disk"
    title = "Unattached persistent disk"

    def evaluate(self, session: Session, context: Any) -> list[RecommendationDraft]:
        drafts: list[RecommendationDraft] = []
        disks = (
            session.execute(select(Resource).where(Resource.resource_type.in_(DISK_TYPES)))
            .scalars()
            .all()
        )
        rows = _rows_by_id(context)
        for disk in disks:
            labels = disk.labels or {}
            attached = disk.status.upper() not in ("DETACHED", "UNATTACHED", "AVAILABLE") and (
                labels.get("attached", "true").lower() != "false"
            )
            if attached:
                continue
            row = rows.get(disk.resource_id)
            observed_cost = row.cost_in_window if row else None
            size_gb = float(labels["size_gb"]) if labels.get("size_gb") else None
            evidence = [
                Evidence(
                    f"disk {disk.resource_name} reports status {disk.status} — it is not "
                    "attached to any instance",
                    metric="disk.status",
                    value=None,
                    threshold=None,
                )
            ]
            if observed_cost is not None and observed_cost > 0:
                evidence.append(
                    Evidence(
                        f"cost in the analysis window is ${observed_cost:.2f}",
                        metric="cost_in_window",
                        value=observed_cost,
                        unit="USD",
                    )
                )
            elif size_gb:
                evidence.append(
                    Evidence(
                        f"size is {size_gb:.0f} GB — estimated at "
                        f"${size_gb * DISK_USD_PER_GB_MONTH:.2f}/month "
                        f"(list-price approximation of ${DISK_USD_PER_GB_MONTH:.2f}/GB-month)",
                        metric="disk.size_gb",
                        value=size_gb,
                        unit="GB",
                    )
                )
            else:
                continue  # neither observed cost nor size — no saving can be shown
            drafts.append(
                self.build_draft(
                    evidence,
                    resource_id=disk.resource_id,
                    resource_label=disk.resource_name,
                    project_id=disk.project_id,
                    service_id=disk.service_id,
                    scope_key=disk.resource_id,
                    problem=(
                        f"{disk.resource_name} is unattached but still billed"
                        + (f" (${observed_cost:.2f} in the window)" if observed_cost else ".")
                    ),
                    recommendation=(
                        "Snapshot the disk, confirm with the owner, then delete it. "
                        "Deletion is irreversible — recovery risk is communicated and "
                        "human approval is required."
                    ),
                    window_start=row.window.start if row else None,
                    window_end=row.window.end if row else None,
                    effort="LOW",
                )
            )
        return drafts

    def explain(self, evidence: list[Evidence]) -> str:
        return (
            "The disk reports a detached state, so its entire cost is paid for storage "
            "no instance reads or writes. " + " ".join(item.statement for item in evidence)
        )

    def calculate_saving(self, evidence: list[Evidence]) -> tuple[float, float, float]:
        observed = next((e.value for e in evidence if e.metric == "cost_in_window"), None)
        if observed is not None and observed > 0:
            return (observed, 0.0, observed)
        size = next((e.value for e in evidence if e.metric == "disk.size_gb"), None)
        if size is not None:
            estimate = size * DISK_USD_PER_GB_MONTH
            return (estimate, 0.0, estimate)
        return (0.0, 0.0, 0.0)

    def calculate_risk(self, evidence: list[Evidence]) -> str:
        return "MEDIUM"  # deleting the wrong disk loses data — snapshot first

    def confidence(self, evidence: list[Evidence]) -> str:
        has_cost = any(e.metric == "cost_in_window" for e in evidence)
        return "HIGH" if has_cost else "MEDIUM"


class StorageRetentionRule(RecommendationRule):
    """Storage hygiene (§18): effectively-unused buckets today; snapshot and
    image retention when provider data exposes them (Phase 9+ extension —
    the mock model has no snapshot/image inventory, so the rule stays silent
    about them instead of inventing findings)."""

    rule_id = "storage_retention"
    title = "Unused storage / retention review"

    def evaluate(self, session: Session, context: Any) -> list[RecommendationDraft]:
        drafts: list[RecommendationDraft] = []
        for row in context.utilization_rows:
            if row.resource_type != "storage_bucket":
                continue
            requests = row.metrics.get("request_count")
            if requests is None or requests.sample_count < STORAGE_MIN_SAMPLES:
                continue
            if requests.avg >= STORAGE_REQUESTS_PER_DAY_MAX:
                continue
            if row.cost_in_window is None or row.cost_in_window <= 0:
                continue
            evidence = [
                Evidence(
                    f"averages {requests.avg:.1f} requests/day over {requests.sample_count} days "
                    f"— below the {STORAGE_REQUESTS_PER_DAY_MAX:.0f}/day unused threshold",
                    metric="request_count.avg",
                    value=round(requests.avg, 2),
                    threshold=STORAGE_REQUESTS_PER_DAY_MAX,
                ),
                Evidence(
                    f"cost in the analysis window is ${row.cost_in_window:.2f}",
                    metric="cost_in_window",
                    value=row.cost_in_window,
                    unit="USD",
                ),
            ]
            drafts.append(
                self.build_draft(
                    evidence,
                    resource_id=row.resource_id,
                    resource_label=row.resource_name,
                    project_id=row.project_id,
                    service_id=row.service_id,
                    scope_key=row.resource_id,
                    problem=(
                        f"{row.resource_name} receives almost no traffic "
                        f"({requests.avg:.1f} requests/day) but costs "
                        f"${row.cost_in_window:.2f} per window."
                    ),
                    recommendation=(
                        "Review the bucket's objects with the owner, then archive to a "
                        "cheaper storage class or delete. Lifecycle policies are preferred "
                        "over manual deletion; recovery risk is low when archiving."
                    ),
                    window_start=row.window.start,
                    window_end=row.window.end,
                    effort="LOW",
                )
            )
        return drafts

    def explain(self, evidence: list[Evidence]) -> str:
        return (
            "Request traffic is effectively zero over two weeks while storage cost "
            "continues. " + " ".join(item.statement for item in evidence)
        )

    def calculate_saving(self, evidence: list[Evidence]) -> tuple[float, float, float]:
        cost = next((e.value for e in evidence if e.metric == "cost_in_window"), None)
        if cost is None or cost <= 0:
            return (0.0, 0.0, 0.0)
        savings = cost * (1 - STORAGE_ARCHIVE_FACTOR)
        return (cost, cost - savings, savings)

    def calculate_risk(self, evidence: list[Evidence]) -> str:
        return "LOW"  # archive path keeps the data; deletion is a human decision

    def confidence(self, evidence: list[Evidence]) -> str:
        return "MEDIUM"


class CostAnomalyRule(RecommendationRule):
    """Cost spikes vs a rolling baseline (§28 phase 1).

    A spike DAY is a (project, service) day whose gross cost exceeds 1.3x its
    trailing 14-day baseline by at least $0.05 — the absolute floor keeps the
    rule quiet on noise that a small lab bill would otherwise amplify. A
    spike INCIDENT needs >= 3 consecutive spike days AND >= $0.50 total excess;
    the estimated impact is exactly that observed excess — nothing invented.
    """

    rule_id = "cost_anomaly"
    title = "Unexpected cost increase"

    def evaluate(self, session: Session, context: Any) -> list[RecommendationDraft]:
        daily = session.execute(
            select(
                CostRecord.project_id,
                CostRecord.service_id,
                CostRecord.usage_date,
                func.sum(CostRecord.cost),
            )
            .group_by(CostRecord.project_id, CostRecord.service_id, CostRecord.usage_date)
            .order_by(CostRecord.usage_date.asc())
        ).all()
        series: dict[tuple[str, str], list[tuple[date, float]]] = defaultdict(list)
        for project_id, service_id, usage_date, cost in daily:
            series[(project_id, service_id)].append((usage_date, money(cost)))

        service_names = _service_display_names(session)
        drafts: list[RecommendationDraft] = []
        for (project_id, service_id), points in sorted(series.items()):
            if len(points) <= ANOMALY_BASELINE_DAYS:
                continue
            runs = self._spike_runs(points)

            for run in runs:
                excess = sum(cost - baseline for _, cost, baseline in run)
                if excess < ANOMALY_MIN_EXCESS:
                    continue
                observed = sum(cost for _, cost, _ in run)
                baseline_total = observed - excess
                peak_day, peak_cost, peak_base = max(run, key=lambda item: item[1] - item[2])
                lift = (peak_cost / peak_base - 1) * 100 if peak_base > 0 else 0.0
                evidence = [
                    Evidence(
                        f"cost ran above 1.3x its {ANOMALY_BASELINE_DAYS}-day baseline for "
                        f"{len(run)} consecutive days ({run[0][0]}..{run[-1][0]})",
                        metric="anomaly.run_days",
                        value=len(run),
                        threshold=ANOMALY_MIN_RUN_DAYS,
                    ),
                    Evidence(
                        f"peak on {peak_day}: ${peak_cost:.2f} vs ${peak_base:.2f} baseline "
                        f"(+{lift:.0f}%)",
                        metric="anomaly.peak_cost",
                        value=round(peak_cost, 2),
                        unit="USD",
                    ),
                    Evidence(
                        f"observed cost over the run ${observed:.2f} vs baseline-level "
                        f"${baseline_total:.2f} — total excess ${excess:.2f} "
                        "(this estimate IS the evidence: cost above the normal run-rate)",
                        metric="anomaly.excess",
                        value=round(excess, 2),
                        unit="USD",
                    ),
                    Evidence(
                        f"observed cost over the run: ${observed:.2f}",
                        metric="anomaly.observed",
                        value=round(observed, 2),
                        unit="USD",
                    ),
                    Evidence(
                        f"baseline-level cost over the same days: ${baseline_total:.2f}",
                        metric="anomaly.baseline_total",
                        value=round(baseline_total, 2),
                        unit="USD",
                    ),
                ]
                service_label = service_names.get(service_id, service_id)
                drafts.append(
                    self.build_draft(
                        evidence,
                        resource_id=None,
                        resource_label=f"{project_id} / {service_label}",
                        project_id=project_id,
                        service_id=service_id,
                        scope_key=f"{project_id}:{service_id}",
                        problem=(
                            f"Daily cost for {project_id} / {service_id} rose "
                            f"{lift:.0f}% above its trailing baseline on {peak_day} and "
                            f"stayed elevated for {len(run)} days (total excess ${excess:.2f})."
                        ),
                        recommendation=(
                            "Investigate what changed around the spike start (new resources, "
                            "traffic, config). No action is automated; the finding is the "
                            "evidence for a later fix or rightsizing."
                        ),
                        window_start=run[0][0],
                        window_end=run[-1][0],
                        effort="LOW",
                    )
                )
        return drafts

    def explain(self, evidence: list[Evidence]) -> str:
        return (
            "Daily cost exceeded a rolling 14-day baseline by more than the noise floor "
            "for several consecutive days — a run-rate change, not a one-off blip. "
            + " ".join(item.statement for item in evidence)
        )

    @staticmethod
    def _spike_runs(
        points: list[tuple[date, float]],
    ) -> list[list[tuple[date, float, float]]]:
        """Consecutive spike runs (day, cost, baseline) — pure, unit-testable.

        A spike day: cost > baseline * ANOMALY_RATIO (strictly) AND
        cost - baseline >= ANOMALY_MIN_DAY_DELTA. A run: >= ANOMALY_MIN_RUN_DAYS
        consecutive spike days.
        """
        runs: list[list[tuple[date, float, float]]] = []
        current: list[tuple[date, float, float]] = []
        for index, (day, cost) in enumerate(points):
            if index < ANOMALY_BASELINE_DAYS:
                continue
            baseline = (
                sum(c for _, c in points[index - ANOMALY_BASELINE_DAYS : index])
                / ANOMALY_BASELINE_DAYS
            )
            delta = cost - baseline
            if baseline > 0 and cost > baseline * ANOMALY_RATIO and delta >= ANOMALY_MIN_DAY_DELTA:
                current.append((day, cost, baseline))
            else:
                if len(current) >= ANOMALY_MIN_RUN_DAYS:
                    runs.append(current)
                current = []
        if len(current) >= ANOMALY_MIN_RUN_DAYS:
            runs.append(current)
        return runs

    def calculate_saving(self, evidence: list[Evidence]) -> tuple[float, float, float]:
        """Savings = the OBSERVED excess over the baseline run-rate, exactly.

        current/potential describe the observed run only — the detail window
        shows those dates; nothing is extrapolated into a fake monthly number.
        """
        excess = next((e.value for e in evidence if e.metric == "anomaly.excess"), None)
        peak = next((e.value for e in evidence if e.metric == "anomaly.peak_cost"), None)
        if excess is None or peak is None or excess <= 0:
            return (0.0, 0.0, 0.0)
        observed = next(
            (e.value for e in evidence if e.metric == "anomaly.observed"),
            None,
        )
        baseline_total = next(
            (e.value for e in evidence if e.metric == "anomaly.baseline_total"), None
        )
        if observed is None or baseline_total is None:
            return (0.0, 0.0, 0.0)
        return (observed, baseline_total, excess)

    def calculate_risk(self, evidence: list[Evidence]) -> str:
        return "MEDIUM"  # investigation may reveal a real incident in progress

    def confidence(self, evidence: list[Evidence]) -> str:
        # A confirmed multi-day run is meaningful, but the rule cannot tell a
        # deliberate change from an incident — medium by design.
        return "MEDIUM"


def _service_display_names(session: Session) -> dict[str, str]:
    from costlab.db.models import Service  # local import avoids a cycle

    return {
        service_id: display
        for service_id, display in session.execute(select(Service.id, Service.display_name)).all()
    }
