# Cost Model — Cloud Cost Lab

> Status: Implemented (Phase 1) · Date: 2026-09-05
> Scope: what "cost" means in this project, how it is stored, aggregated, and served.

---

## 1. Data provenance (read this first)

Every number served by the Phase 1 API is **synthetic**:

- generated once by `scripts/generate_mock_data.py` with fixed seeds (`COST_SEED=42`, `USAGE_SEED=43`);
- committed as `data/mock/*.json` so demos and tests are byte-identical on every machine;
- loaded into PostgreSQL by the mock provider (`MockBillingProvider`) — no GCP credentials involved (`DEMO_MODE=true`).

Treat every figure as `MOCK — estimated`. Real Billing Export data arrives in Phase 9 (ADR-004); the schema is designed so that switch is a provider swap, not a rewrite.

## 2. Core entities

| Table | Grain | Notes |
| --- | --- | --- |
| `projects` | one GCP-style project | carries `environment` + labels; the `cc-lab-legacy-sandbox` project deliberately lacks owner/team/application labels to demo **UNALLOCATED** cost |
| `services` | one GCP service slug | `compute-engine`, `cloud-sql`, `cloud-storage`, `artifact-registry` |
| `resources` | one billable resource | `resource_id`, `resource_name`, `type`, project, region, environment, status, `owner`, `team`, `application` (nullable on purpose) |
| `cost_records` | one resource × one day × one SKU | the fact table all cost analytics read |
| `resource_usage` | one resource × one day | utilization metrics; nullable per metric because not every resource exposes every metric |

Environments supported: `development`, `staging`, `production` — validated at the provider boundary (pydantic `Literal`) and stored on every cost row, so environment breakdowns never require joins.

## 3. Cost fields

```text
cost      = gross cost of the resource-day (USD)
credits   = discounts applied (mock: 5% simulated committed-use discount on production rows)
net_cost  = cost - credits        ← always verify: net_cost == cost - credits
currency  = "USD"
```

Money is stored as `Numeric(14, 6)` (exact Decimal), **never float**, and summed in SQL (`SUM`) before being rounded to 4 decimals at the response boundary. The `credits`/`net_cost` split matters because FinOps reporting must show both gross and net spend.

## 4. Time granularity

- **Daily** — native grain of `cost_records.usage_date`.
- **Weekly** — ISO week buckets via `date_trunc('week', ...)`; weeks start on **Monday**, matching how billing exports bucket weeks.
- **Monthly** — `date_trunc('month', ...)`.

`GET /api/cost/trend?granularity=day|week|month` returns `period` = first day of the bucket. All three granularities sum to the same total for the same period — that invariant is asserted by tests.

## 5. Reporting period semantics

`start_date` / `end_date` default to **the bounds of the available data, not the wall clock**. The mock dataset is date-anchored (2026-06-01 → 2026-09-05); wall-clock defaults would silently return empty reports whenever data is older than "today − 30 days". This also matches real FinOps behaviour, where billing export has freshness lag (FRESH/STALE labelling comes in Phase 10).

## 6. Cost dimensions

Every endpoint filters/groups by: `project_id`, `service` (slug), `environment`, `region`, `resource_id`, plus date range. Missing attribution (e.g. the legacy sandbox resource with no `team`/`owner`/`application`) is reported as-is with empty labels — the platform never guesses ownership; the UI will label it **UNALLOCATED** (Phase 2+).

## 7. Scenario data baked into the dataset

| Scenario | Where | Evidence to look for |
| --- | --- | --- |
| Rising cost trend | all months | Jun $45.23 → Jul $52.50 → Aug $61.20 gross |
| Compute spike (+35%) | 2026-08-10 … 2026-08-16 | weekly trend jump inside August |
| Budget-risk run-rate | September | Sept daily run-rate is the highest of the window |
| Idle VM | `vm-report-dev-1` | CPU < 5%, minimal network, daily |
| Oversized VM | `vm-etl-staging-1` | e2-standard-4 at ~11% CPU |
| Underutilized Cloud SQL | `sql-shop-orders-staging` | ~12% CPU |
| Unallocated cost | `cc-lab-legacy-sandbox` / `vm-legacy-sandbox-1` | labels missing team/owner/application |
| Dev weekend dip | dev VMs | weekend usage ×0.35 |

Recommendations are NOT generated yet — detection rules arrive in Phase 4. The dataset only needs to contain the evidence those rules will consume.

## 8. Known simplifications (honest list)

- One SKU per resource per day; real billing exports split by SKU/credit type far more finely.
- Credits are a flat simulated 5% on production rows, not real discount instruments.
- Usage metrics are daily aggregates, not hourly samples; `latency_ms` is always null until application metrics exist.
- All resources are always-on (`usage_amount = 24 hours`); scheduling-based savings (Phase 4+) will need the mock data extended.
- Multi-cloud, multi-currency, and amortization are out of scope for Phase 1.
