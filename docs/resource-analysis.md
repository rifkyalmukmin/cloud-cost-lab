# Resource Utilization Analysis — Cloud Cost Lab (Phase 4)

> Status: Implemented · Date: 2026-09-12
> The cost ↔ utilization evidence layer: `GET /api/utilization`, `GET /api/utilization/{id}` and the `/utilization` page.
> **Phase 4 is evidence only — no recommendations.** The recommendation engine (a later phase) is the consumer of this evidence.

---

## 1. Why this phase exists

Phase 3 linked cost to resources ("what does it cost?"). Phase 4 answers "what is it
doing?" — the per-resource utilization picture that turns a cost table into an
engineering signal. Cost without utilization cannot distinguish an overprovisioned
VM from a busy one; utilization without cost cannot rank what matters. Both are
joined here over the **same time window**, so numbers are comparable.

## 2. Metrics and stats

Stored daily per resource (`resource_usage`, one row per resource per day; every
column nullable — not every resource exposes every metric):

| Metric | Unit | Exposed by (in the mock dataset) |
| --- | --- | --- |
| CPU utilization | % (0–100) | VMs, Cloud SQL |
| Memory utilization | % | VMs, Cloud SQL |
| Disk utilization | % | VMs, Cloud SQL |
| Network in / out | MB/day | all resources |
| Request count | count/day | Cloud Storage, Artifact Registry |
| Latency | ms | modeled, but the mock dataset has **no samples** |
| Error rate | % | Cloud Storage, Artifact Registry |

Per metric, per resource, per window (computed in **one SQL grouped query**):

- `avg` — the representative level; sensible only when the workload is stable;
- `min` / `max` — the observed range;
- `stddev` (sample) — day-to-day swing; `null` with fewer than 2 samples;
- `p95` — the 95th percentile via Postgres `percentile_cont(0.95)` (linear
  interpolation at rank `0.95·(n−1)`);
- `sample_count` — how many non-null samples fed the stats.

**Teacher note — why P95 matters:** averages hide spikes. A VM averaging 30% CPU
with a P95 of 75% behaves very differently from one with a P95 of 32%, even though
the means match. P95 says "95% of days were below this" — the level a resize would
have to accommodate. Latency and request metrics are the classic P95 territory
(SLO language); here it is exposed for every metric since the SQL costs the same.

### Zero vs null vs missing — a hard rule

- **0 is an observation.** A CPU sample of 0% is real data and stays in
  `avg/min/max/P95`.
- **null is a gap in a row** (that resource does not expose that metric that day) —
  excluded from that metric's aggregates, never treated as 0.
- **missing is zero samples in the whole window** — the metric is reported through
  `missing_metrics` and has no entry in `metrics`, never a fabricated 0.

This is why the mock dataset's `latency_ms` (no samples at all) shows up as missing
for **every** resource, while a VM's quiet 0% CPU day stays inside its average.

## 3. Time window

`start_date` / `end_date` query params, defaulting to the full span of the
utilization **data** (data-anchored, never the wall clock — same philosophy as the
cost endpoints; `start_date > end_date` → `422`). Cost linkage sums cost records
inside the **same window**, so the Cost-vs-Utilization view compares like with like.

## 4. Evidence signals (project-specific heuristics — not standards)

Computed from **CPU** when CPU samples exist; otherwise all three are `null`
("no signal" must be distinguishable from "signal = false"):

| Signal | Rule | Rationale |
| --- | --- | --- |
| `low_utilization` | avg CPU < 20% | aligns with the rightsizing evidence rule (CLAUDE.md §17) |
| `high_utilization` | avg CPU > 80% | sustained saturation — performance risk territory |
| `unstable_utilization` | CPU stddev > 15 points **and** ≥ 7 samples | a wildly swinging workload makes its average meaningless; one week is the minimum to judge stability |

`missing_cpu` counts resources with **no CPU samples** (storage buckets, artifact
registries — and anything the provider does not instrument).

These flags are **evidence for humans and for the future recommendation engine** —
this phase renders them, it never converts them into "resize/delete this" advice,
and nothing is automated (CLAUDE.md §22 lifecycle starts in the recommendation
phase; §38 keeps the platform in observation/recommendation modes).

## 5. API

### `GET /api/utilization`

- Filters: `project_id`, `service`, `environment` (+ `start_date`, `end_date`),
  pagination `page` / `page_size` (cap 100).
- Response: `window`, `pagination`, `signal_counts` (over the **full filtered
  set**, not the page) and `items[]` — each item carries resource identity,
  `metrics{}` (only metrics with samples), `missing_metrics[]`, `avg_cpu`,
  `cost_in_window` / `cost_credits_in_window` / `cost_net_in_window` and `signals`.
- Ordering: avg CPU DESC, resources without CPU last, ties by resource id.

### `GET /api/utilization/{resource_id}`

Everything above for one resource plus `series[]` — the daily samples within the
window, date ascending (same shape as the Phase 3 detail utilization series).
Unknown id → structured `404` with request id. A resource that exists but has no
usage rows in the window returns all metrics as missing — missing data is not a
missing resource.

### Query-engine notes (why two subqueries)

Usage stats and window cost are computed in **separate grouped subqueries** that
are outer-joined to `resources`. Aggregating usage *after* joining cost would
fan out usage rows (a resource can have several cost lines per day — multiple
SKUs) and silently corrupt every count, average and P95. The subquery shape also
keeps the result bounded at one row per resource; page slicing happens on those
computed rows and signal counts stay exact across pages.

## 6. Dashboard — `/utilization`

- Evidence summary cards: low / high / unstable / no-CPU counts over the filtered set.
- Filters: project, service, environment (options fetched from the API).
- **Cost vs Utilization chart**: one bubble per resource, cost-in-window (y) vs
  avg CPU (x), bubble color = evidence signal, dashed reference lines at the 20% /
  80% thresholds. Resources without CPU samples plot nothing here (they remain in
  the table) — the chart never invents an x value.
- Per-resource table: Avg CPU, P95 CPU, Avg Memory, CPU σ, Cost (window), evidence
  badges, missing-metric count; rows link to the Phase 3 resource detail view.
- Every section uses the standard loading / error / empty / success states.

## 7. Testing

`apps/api/tests/test_utilization.py` (19 tests, PostgreSQL test DB seeded with the
mock dataset):

- **aggregation** — avg/min/max/stddev recomputed independently from
  `data/mock/usage.json` for compute and network metrics;
- **P95** — endpoint equals the `percentile_cont` definition (linear
  interpolation), plus single-sample and two-point edge cases;
- **missing values** — storage/registry resources lack CPU/memory/disk;
  `latency_ms` missing everywhere; request metrics missing for VMs;
- **null** — per-row nulls excluded from aggregates (sample_count < window days);
- **zero values** — the dataset's 0% CPU days stay inside the stats (`min == 0`)
  and are not flagged missing;
- **time range** — explicit sub-window narrows window, stats, series and cost;
  inverted range → `422`;
- **signals** — classification unit-tested with synthetic stats (low/high/boundary/
  unstable/insufficient-samples/missing), plus dataset-driven low signal and
  zero high signal; counts proven to cover the full filtered set on every page;
- **cost linkage** — window cost equals a recomputation from `data/mock/cost.json`;
- pagination (disjoint pages, beyond-end, `page=0` → 422), filters, empty result,
  unknown resource 404.

## 8. Limitations

- Signals are CPU-only by design; memory/disk-based rules arrive with the
  recommendation engine where each rule owns its evidence.
- Utilization is daily; intra-day spikes need finer-grained monitoring data (Phase 9+).
- The list endpoint aggregates on demand; at real fleet scale this belongs in a
  scheduled rollup table rather than a live query.
- No recommendations are produced here — by design, per the phase scope.
