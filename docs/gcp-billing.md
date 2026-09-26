# GCP Billing Integration — Cloud Cost Lab (Phase 8)

> Status: Implemented (code-complete, dormant in demo mode) · Date: 2026-09-13
> Pipeline: **GCP Billing Export → BigQuery → Cloud Cost Lab**, behind the same `BillingDataProvider` abstraction the mock provider satisfies (ADR-003).
> **Nothing billable was created for this phase** — see `docs/gcp-setup.md` for the inspection and the manual, human-approved enablement steps.

---

## 1. Architecture

```text
GCP Billing Account
      │  (daily export job, configured in Cloud Console — manual step)
      ▼
BigQuery dataset  cloud_cost_lab_billing
      │  table gcp_billing_export_v1_<billing account id>
      ▼
GCPBillingProvider  (partition-aware, column-whitelisted, bounded query)
      │  maps rows → BillingSnapshot (validated by pydantic at the boundary)
      ▼
ingestion loader → PostgreSQL → analytics → dashboard
```

Provider selection lives in `build_providers()` (`providers/__init__.py`):

- `DEMO_MODE=true` (default) → `MockBillingProvider` + `MockUsageProvider`
  (the demo dataset — unchanged, all tests keep passing);
- `DEMO_MODE=false` → `GCPBillingProvider` + `EmptyUsageProvider`
  (real *utilization* via Cloud Monitoring is a later phase; real-mode usage
  contributes no samples so utilization surfaces stay honest — mock numbers
  are never mixed with real billing);
- real mode without `GCP_BILLING_PROJECT/DATASET/TABLE` fails loudly.

Both providers implement `BillingDataProvider.load_snapshot() →
BillingSnapshot` — nothing above the providers knows which mode is active.

## 2. Configuration (environment only, §8)

```text
GCP_BILLING_PROJECT=learn-cloud-gcp-506920
GCP_BILLING_DATASET=cloud_cost_lab_billing
GCP_BILLING_TABLE=gcp_billing_export_v1_012C25...
GCP_BILLING_LOCATION=US
GCP_BILLING_MAX_DAYS=92        # bounded query range
GCP_BILLING_MAX_ROWS=100000    # hard row cap
FRESHNESS_MAX_HOURS=48         # FRESH/STALE threshold
```

Credentials are **never** in code or files: local development uses
Application Default Credentials; deployment uses Workload Identity Federation
where feasible (§36). The provider takes injected client/job-config factories,
so tests run without the Google libraries and production never touches key
files. `google-cloud-bigquery` is an **optional** dependency (`pip install -e
'.[gcp]'`) — the demo image stays small; missing package → clear
`GCPBillingError`.

## 3. Row mapping (export → snapshot)

| Export column | Snapshot field | Notes |
| --- | --- | --- |
| `DATE(usage_start_time)` | `usage_date` | day bucket |
| `project.id` / `project.name` | project | one `ProjectInput` per project |
| `service.description` | service | slugified id (`Compute Engine` → `compute-engine`) |
| `sku.description` | `sku` | |
| `resource.global_name` / `resource.name` | resource | full URI kept as id; **`type` is a coarse `gcp_resource`** — the export schema has no type column and we do not guess |
| *no resource on the row* | pseudo-resource `unattributed:{project}:{service}` | honest bucket (`type=unattributed`, `status=UNATTRIBUTED`) so unattributed cost is visible, never silently dropped |
| `location.region` | `region` (`global` fallback) | |
| `labels` (ARRAY<STRUCT>) | labels dict | malformed pairs dropped, row still valid |
| label `environment` ∈ dev/staging/prod | `environment` | anything else (or missing) → **`UNALLOCATED`** — attribution is never guessed (§12) |
| `SUM(cost)`, `SUM(credits)` | `cost`, `credits`, `net_cost = cost − credits` | |

Malformed rows (missing/invalid columns) raise `GCPBillingError` at the
boundary — a half-validated fact never reaches PostgreSQL.

## 4. BigQuery cost protection (§9 — enforced by tests)

The executed query (see `providers/gcp.py`, `QUERY_TEMPLATE`):

- filters **`_PARTITIONTIME`** (partition-aware) and `usage_start_time`;
- an explicit **column whitelist** — never `SELECT *`;
- **date range capped** by `GCP_BILLING_MAX_DAYS` (default 92), ending
  yesterday (the running day is not final);
- **`LIMIT @max_rows`** hard cap (default 100 000);
- **query parameters** — no value is ever string-interpolated;
- a **dry run first**, logging the bytes that would be scanned.

## 5. Data freshness (§41)

`GET /api/freshness` returns `last_updated` (newest data day),
`data_age_hours` (measured to the end of that UTC day), `max_age_hours`
(configurable) and `status`:

- `FRESH` — age ≤ 48h (default);
- `STALE` — age > 48h;
- `UNKNOWN` — no data at all.

The Overview page renders the status chip + age next to the headline numbers;
stale data is never presented as current. The demo dataset ends 2026-09-05,
so demo mode honestly reports **STALE**.

## 6. Testing (all with stubbed BigQuery clients — no network, no credentials)

Valid mapping (cost/credits/net, labels, slugified services, UNALLOCATED
fallback, unattributed buckets) · empty response · BigQuery error wrapped with
context · authentication failure with an actionable message · missing package
message · malformed row fails at the boundary · query safety assertions
(partition filter, no `SELECT *`, LIMIT, parameters, dry-run-before-query) ·
demo-mode wiring unchanged (`test_mock_provider.py` still passes) · real mode
without config fails loudly · freshness FRESH/STALE/UNKNOWN including the
48h inclusive boundary. `tests/test_providers_gcp.py` (14 tests, 148 total).

## 7. Limitations

- Real **usage/utilization** (Cloud Monitoring) is not integrated yet — real
  mode runs with empty utilization and honest "no data" surfaces.
- Resource `type`/`machine_type`/`created_at` are coarse or empty until a
  Cloud Asset Inventory enrichment lands.
- The export lags ~a day by design; freshness surfaces this instead of
  hiding it.
