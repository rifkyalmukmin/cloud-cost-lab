# GCP Monitoring Integration — Cloud Cost Lab (Phase 9)

> Status: Implemented (code-complete, dormant in demo mode) · Date: 2026-09-13
> Pipeline: **Cloud Monitoring time series → GCPMonitoringProvider → the same usage contract as the mock** — connecting COST + UTILIZATION + PERFORMANCE.
> Nothing billable was created; activation is a documented manual step (see `docs/gcp-setup.md` §2 posture).

---

## 1. Architecture

```text
Cloud Monitoring API (monitoring.googleapis.com)
      │  per-metric time-series queries, daily alignment (injected runner)
      ▼
GCPMonitoringProvider
      │  merges per (resource, day) → list[UsageRecordInput] (pydantic-validated)
      ▼
ingestion loader → PostgreSQL resource_usage → utilization analytics → recommendations
```

Provider selection (`build_providers()`):

- `DEMO_MODE=true` → `MockMonitoringProvider` (the committed dataset — unchanged);
- `DEMO_MODE=false` + `GCP_MONITORING_PROJECT` → `GCPMonitoringProvider`;
- real billing without monitoring config → `EmptyMonitoringProvider` (utilization
  surfaces honestly show missing data — mock numbers are never mixed with real
  billing).

`MockUsageProvider`/`UsageDataProvider` remain as backward-compatible aliases of
`MockMonitoringProvider`/`MonitoringDataProvider`.

## 2. Metrics collected

| Field | Monitoring metric | Notes |
| --- | --- | --- |
| CPU | `compute.googleapis.com/instance/cpu/utilization` | unit 0–1 → scaled to % |
| Memory | `agent.googleapis.com/memory/percent_used` | requires Ops Agent — may be absent |
| Disk | `agent.googleapis.com/disk/percent_used` | requires Ops Agent — may be absent |
| Network in/out | `instance/network/received_bytes_count` / `sent_bytes_count` | bytes → MB |
| Connections | `cloudsql.googleapis.com/database/mysql/connections` | new `connections` metric (migration 0004, `resource_usage.connections`) |
| Requests | `loadbalancer.googleapis.com/https/request_count` | SUM alignment |

Every metric is a `MetricQuery` descriptor (metric type, unit scale, reducer
MEAN/SUM). Missing series → the field stays `null` in the record; the
utilization API already reports them through `missing_metrics` — never as 0
(the Phase 4 hard rule).

## 3. Guarantees (all test-asserted)

- **Provider failure** — any metric query failure (wrapped at provider level)
  raises `GCPMonitoringError` and aborts the load: a partial utilization
  picture (real CPU, no memory) must never be mistaken for a complete one.
- **Missing metrics** — no series ⇒ `null` fields, never zeros.
- **Zero metrics** — observed zeros are real observations and are kept.
- **Stale metrics** — a series whose newest sample is older than
  `GCP_MONITORING_MAX_AGE_DAYS` (default 7) is dropped with a log line;
  ingesting stale samples as current would misstate utilization.
- **Bounded window** — `GCP_MONITORING_MAX_DAYS` (default 30), ending
  yesterday; **auth** via ADC locally / WIF in deployment; the runner and
  client are injected so tests need no Google packages (optional `gcp` extra:
  `google-cloud-monitoring`).

## 4. Strengthened recommendations (cost alone is never enough)

The Phase 5 rules already join cost + utilization + duration. Phase 9 adds
**performance corroboration** from monitoring to `IdleComputeRule`:

- a resource averaging more than 10 requests/day is **never** idle;
- a resource averaging more than 2 open connections is **never** idle;
- when present, request/connection averages become extra evidence lines.

Example (the phase brief): Cost $30/month, CPU 6% (idle band), 30 stable days,
requests ~2/day → idle recommendation whose evidence names the cost, the CPU
average, the day count and the request average. Cost alone ($30/month, no
monitoring data) produces **nothing** — unit-tested.

## 5. Configuration

```text
GCP_MONITORING_PROJECT=learn-cloud-gcp-506920
GCP_MONITORING_MAX_DAYS=30
GCP_MONITORING_MAX_AGE_DAYS=7
```

## 6. Testing

`tests/test_providers_monitoring.py` (15 tests): valid multi-metric mapping
with unit scaling (CPU 0–1 → %, bytes → MB) · missing metrics ⇒ null · zero
metrics kept · stale series dropped (and within-age kept) · provider failure
wrapped · partial-metric failure fatal · missing-package message · mock
monitoring still loads · factory wiring (real mode with/without monitoring).
Plus the idle-rule evidence tests in the same file, and the Phase 4/5 suites
verifying no regressions (163 total).

## 7. Limitations

- The default runner uses `instance_id`/`database_id` resource labels as the
  resource id — matching against billing-export resources may need a mapping
  table at scale.
- Ops-Agent metrics (memory/disk) exist only where the agent runs; the mock
  dataset carries no `connections` samples yet (generator will emit them in a
  future dataset refresh) — connections show as missing there.
- MQL/rate alignment for network counters is simplified (daily mean of the
  counter); production hardening belongs with Phase 11+ monitoring work.
