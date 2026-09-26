# Recommendation Engine — Cloud Cost Lab (Phase 5)

> Status: Implemented · Date: 2026-09-13
> Evidence-backed, human-approved optimization findings: five rules, a priority model, the `recommendations` table and the `/recommendations` page.
> **The engine never modifies infrastructure.** It writes rows to this application's own database; every recommendation carries `approval_required = true`.

---

## 1. Design (CLAUDE.md §22–§24, §38)

The engine answers the seven questions every recommendation must answer:
**what is wrong, what evidence supports it, how much could be saved, what is the
risk, how much effort is required, who approves, what happens next.**

- Rules are pluggable classes implementing the `RecommendationRule` interface
  (`costlab/recommendations/base.py`): `evaluate()`, `explain()`,
  `calculate_saving()`, `calculate_risk()`, `confidence()`.
- `evaluate()` returns drafts **only** when observed evidence passes every
  guard — a rule that cannot prove its claim stays silent (false positives are
  worse than silence).
- Money math derives from the evidence values themselves; nothing is invented.
  Savings are **potential**, never realized — realized savings require the
  later verification phase (§23).
- Lifecycle: `OPEN → APPROVED / REJECTED` (human decision via API/UI).
  `IMPLEMENTED` and `VERIFIED` exist in the model but their transitions arrive
  with the savings-tracking phase.
- Engine run (seed or `POST /api/recommendations/run`) upserts by
  `(rule_id, scope_key)`, **preserves human decisions** on unchanged findings,
  and removes findings whose evidence disappeared. It is recommendation mode
  only (§38 mode 2) — no cloud resource is read, written, or destroyed.

## 2. The five rules

All thresholds are **project-specific heuristics** (lab-scale, ~$60/month) —
documented here, visible in the UI, not industry standards.

### IdleComputeRule (`idle_compute`) — §16

| Guard | Threshold | Purpose |
| --- | --- | --- |
| avg CPU | < 5% (strict) | sustained near-zero load |
| P95 CPU | ≤ 20% | **burst guard** — a low average with spiky P95 may be batch work |
| network in+out avg | < 100 MB/day | minimal traffic |
| samples | ≥ 7 days | at least a week |
| cost in window | > 0 | nothing to save without cost evidence |
| CPU samples | required | null CPU ⇒ silence, never a guess |

Saving: development ⇒ scheduling scenario (off-hours), estimated 60% of window
cost; non-development ⇒ decommission scenario, 100% of window cost (risk MEDIUM,
owner verification required). Effort LOW (dev) / MEDIUM.

### OversizedComputeRule (`oversized_compute`) — §17

| Guard | Threshold |
| --- | --- |
| avg CPU | < 20% (strict) |
| avg memory | < 40% (strict) |
| P95 CPU | ≤ 40% (headroom must survive the resize) |
| CPU stddev | ≤ 15 points (stable ⇒ the mean is meaningful; null ⇒ silence) |
| samples | ≥ 14 days |
| machine type | must be a known shape (one-step-down map) |

Proposes the same-family one-step-down shape (e.g. `e2-standard-4 →
e2-standard-2`), saving estimated at 50% of window cost (listed-price ratio
approximation — labelled a SIMULATION-grade estimate in the UI). Production
risk MEDIUM, otherwise LOW. Drafts declare `suppressed_by = ["idle_compute"]`:
when the idle rule fires for the same resource, the engine drops the oversized
finding (the more specific action wins).

### UnusedDiskRule (`unused_disk`) — §18

Fires for `disk`/`persistent_disk` resources reporting a detached state
(`status` or `attached=false` label). Saving = observed window cost, or a
size-based estimate (`$0.04/GB-month`, list-price approximation) when cost data
is missing. Risk always MEDIUM — deletion is irreversible, snapshot first.
**The mock dataset contains no disk resources, so this rule produces nothing
there** (tested with a synthetic detached disk).

### StorageRetentionRule (`storage_retention`) — §18

Today: storage buckets averaging < 10 requests/day over ≥ 14 days ⇒ unused
storage; saving estimated via the archive-tier ratio (80% of window cost,
potential = 20%). Snapshot/image/retention-policy branches need provider
inventory data that the Phase 1–5 data model does not carry — the rule stays
silent about them (extension point for Phase 9+). Risk LOW (archive keeps data).

### CostAnomalyRule (`cost_anomaly`) — §28 phase 1

Rolling-average + threshold on **daily cost per (project, service)**:

- a spike DAY: cost > 1.3× its trailing 14-day baseline (strict) **and**
  ≥ $0.05/day — the absolute floor suppresses noise a small bill would amplify;
- a spike INCIDENT: ≥ 3 consecutive spike days **and** total excess ≥ $0.50;
- `potential_savings` = the observed excess over the baseline run-rate —
  the estimate IS the measurement, nothing extrapolated.

`resource_id` is null for anomalies (project/service scoped); the window
carries the spike dates. Confidence MEDIUM by design (a run-rate change cannot
be distinguished from a deliberate one without human context). Effort LOW
(investigate).

## 3. Priority model (§24, project-specific)

```
score = 40·savings_component + 25·confidence + 20·risk⁻¹ + 15·effort⁻¹
savings_component = min(1, potential_savings / $10)   # lab-scale saturation
confidence HIGH/MEDIUM/LOW = 1.0/0.6/0.3
risk⁻¹       LOW/MEDIUM/HIGH     = 1.0/0.5/0.0
effort⁻¹     LOW/MEDIUM/HIGH     = 1.0/0.5/0.0
label: ≥ 70 HIGH · ≥ 45 MEDIUM · else LOW
```

## 4. Data & persistence

`recommendations` table (migration `0002`): identity (uuid), rule/scope keys,
linkable `resource_id` (null for scope-level findings), `problem`, `evidence`
(JSONB list of statement+metric+value+threshold), `recommendation` text, the
four money fields, `risk/confidence/effort`, `priority_score/priority`,
`approval_required`, `status`, window dates, timestamps. Unique
`(rule_id, scope_key)` makes re-runs idempotent; indexes cover status+priority
lookups. Demo seeding runs the engine so the UI has findings immediately.

## 5. API

- `GET /api/recommendations` — filters `status`, `rule_id`, `risk` (severity),
  `priority`, `resource_id`, `project_id`; `sort = priority | savings |
  recent`; pagination. Summary carries per-status counts and
  `open_potential_savings` (OPEN + APPROVED — savings awaiting implementation).
- `GET /api/recommendations/{id}` — full detail; structured 404.
- `POST /api/recommendations/run` — re-run the engine (status-preserving).
- `POST /api/recommendations/{id}/approve` · `/{id}/reject` — human decisions;
  only `OPEN` rows may transition (otherwise `409`).
- Invalid filter values → `422`.

## 6. UI — `/recommendations`

- Summary cards: Open / Approved / Rejected / potential savings (open+approved).
- Filters: status, rule, severity (risk), priority; sort by priority score,
  savings or recency; server-side pagination.
- Table: title + rule badge, resource, current/potential/saving (+percentage),
  priority, severity, status — rows link to the detail page.
- Detail page: money cards, **What is wrong**, **Evidence** (statements with
  raw metric/threshold values), **Recommendation** with risk/confidence/
  effort/priority badges, and the **Human approval** card — Approve/Reject
  buttons for OPEN rows (decision only, never an action).
- `Run analysis` button triggers `POST /run`.

## 7. Dataset findings (deterministic demo)

`POST /run` on the mock data yields exactly **5** findings — no false positives:

| Finding | Evidence summary |
| --- | --- |
| Idle: `vm-report-dev-1` | avg CPU 2.0%, P95 3.3%, net ~16 MB/day, $2.09/window |
| Oversized: `vm-etl-staging-1` | CPU 11.0% / mem 30.3% stable on e2-standard-4 → e2-standard-2 |
| Oversized: `vm-legacy-sandbox-1` | CPU 12.1% / mem 27.3% on e2-medium (unowned) |
| Anomaly: shop-prod / compute | 3-day run 2026-08-10..12, ~$0.72 excess |
| Anomaly: shop-dev / compute | multi-day September rise, ~$0.52 excess |

Guarded non-findings (asserted in tests): `vm-sandbox-dev-1` (CPU 22.6% — above
the oversized boundary), healthy prod VMs, Cloud SQL (different rule, later
phase), storage buckets (real traffic), the legacy sandbox's noise-level cost
jitter (absolute floor).

## 8. Testing

`apps/api/tests/test_recommendations.py` (24 tests):

- **boundary ladder** — CPU 0 / 4.99 / 5.0 / 10 / 20 / null for idle and
  oversized (5.0 and 20.0 exactly are NOT flagged: strict inequalities);
- guards — P95 burst guard (20.0 passes, 20.1 fails), network floor,
  insufficient samples, missing cost evidence, undefined stddev, unknown
  machine type, non-VM resources;
- money math — scheduling vs decommission saving, resize 50%, percentage
  consistency, priority saturation/labels (70.0 → HIGH, 69.9 → MEDIUM);
- anomaly runs — flat series silent, 1.3× exactly silent, 1-day and 2-day runs
  silent, 3-day run fires, separated incidents produce two runs;
- dataset — the exact 5-findings set, full evidence on every row, suppression,
  idempotent re-run, filters/sort/pagination/422/404;
- lifecycle — approve → 409 on re-approve/reject, reject, **status preserved
  across a re-run**, status filter.

## 9. Limitations

- No automated execution: implementation/verification transitions and the
  audit trail arrive with the savings-tracking phase (§23, §8).
- Anomaly detection is rolling-average + threshold (§28 phase 1); z-score and
  per-resource granularity are future work.
- Snapshot/image retention branches await provider inventory (Phase 9+).
- Savings estimates use list-price ratios, not quotes; Cloud SQL rightsizing
  is deliberately out of scope here (§19, cautious separate rule later).
