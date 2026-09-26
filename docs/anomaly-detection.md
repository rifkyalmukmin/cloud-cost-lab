# Anomaly Detection — Cloud Cost Lab (Phase 7)

> Status: Implemented · Date: 2026-09-13
> Unexpected-cost-increase detection: `GET /api/anomalies` and the `/anomalies` page (CLAUDE.md §28 phase 1 + z-score).
> **Detection is advisory** — findings feed human review and the Phase 5 approval workflow; nothing is acted upon automatically.

---

## 1. Detection model

For every **(project, service, resource)** daily net-cost series:

- **expected** = mean of the previous 14 *available* days (the rolling
  baseline);
- **z-score** = (actual − expected) ÷ baseline standard deviation;
- **one-sided** — only increases (actual > expected) are anomalies; decreases
  are savings, not incidents;
- **noise floor** — a day must clear ALL of: difference ≥ $0.05, change
  ≥ +25%, z ≥ 2.0 (tunable via `min_z_score`). The absolute floor stops a
  small bill's jitter from manufacturing incidents.

### Edge behaviour (all unit-tested)

| Case | Behaviour |
| --- | --- |
| Warm-up period (first 14 days) | never flagged — no baseline exists |
| Zero baseline (expected = 0) | skipped — spend appearing from nothing is new spend, not a jump over a run-rate |
| Mixed zero/spend window | surfaces once the baseline includes some spend (a real, large percentage jump) |
| Zero-variance baseline (σ = 0) | z undefined → the step-change still surfaces through the percentage path with `z_score: null`, severity LOW, confidence LOW — never a fabricated z |
| Missing days | gaps are absent, not zeros — the baseline uses the last 14 *available* days |

## 2. Severity and confidence

| Severity | Rule |
| --- | --- |
| HIGH | z ≥ 4.0 or change ≥ +100% |
| MEDIUM | z ≥ 3.0 or change ≥ +60% |
| LOW | z ≥ 2.0 (the minimum) |

Confidence reflects evidence quality: HIGH with ≥ 10 baseline samples and
z ≥ 3; MEDIUM with ≥ 7 samples; LOW otherwise. Zero-variance step-changes are
always LOW confidence.

## 3. Fields (per finding)

`date`, `service` (id + display name), `project` (id + display name),
`resource` (id + display name, null for scope-level series), `actual`,
`expected`, `difference` (actual − expected), `percentage_change`,
`z_score` (nullable), `severity`, `confidence`, `baseline_samples`.

## 4. Relationship to the Phase 5 CostAnomalyRule

The recommendation engine's `CostAnomalyRule` (Phase 5) groups consecutive
spike days into **run-level findings** ("cost rose above baseline for N days")
with an excess-cost estimate, feeding the human approval workflow. This
module exposes the **point-level detections** (individual days) behind the
same phenomenon, at resource granularity where the data supports it. The two
share the same noise-floor philosophy but answer different questions:
"what should I act on?" (rule) vs "exactly which day/resource jumped?" (this).

## 5. API — `GET /api/anomalies`

- Filters: `severity`, `min_z_score` (1–10, default 2.0), `project_id`,
  `service`, `environment` (resolved to project ids), `resource_id`;
  pagination; invalid values → 422.
- Summary: total, counts by severity, counts by service. Items sorted newest
  first, then by z-score.

## 6. UI — `/anomalies`

- Summary line: total and per-severity counts.
- Filters: severity and minimum z-score (2.0 / 3.0 / 4.0) with reset.
- Table: date, resource (linked to the Phase 3 detail view) + project,
  service, actual vs expected, difference (+$), change (+%), z-score,
  severity badge, confidence with baseline sample count.
- The detection rules — warm-up, noise floor, one-sided, flat-baseline
  handling — are printed on the page so the numbers are self-explanatory.

## 7. Testing

In `apps/api/tests/test_forecast_anomalies.py` (pure scenarios on synthetic
series + dataset/API checks):

- **normal trend** — noisy-but-flat series produces nothing;
- **spike** — a +100% single day is detected with exact fields and severity;
- **large spike** — +900% ⇒ HIGH severity, z ≥ 4;
- **zero baseline** — all-zero windows skipped; mixed-window jump surfaces;
- **zero-variance baseline** — z null, severity/confidence LOW;
- **missing values** — gaps shrink nothing, baseline = 14 available days;
- **insufficient warm-up** — a huge value on day 2 is never flagged;
- dataset/API — the designed spike week and September rise produce ≥ 10
  resource-level findings with HIGH severity present, field consistency
  (difference = actual − expected, percentage math), newest-first ordering,
  filters, stricter z thresholds, pagination disjointness, and 422s.
