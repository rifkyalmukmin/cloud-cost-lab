# BigQuery Cost Protection — Cloud Cost Lab

> Status: Documented + enforced in code · Date: 2026-09-13
> On-demand BigQuery pricing is ~$5/TB scanned. The billing export table is partitioned by day; every query this platform runs is designed to scan megabytes, not gigabytes (CLAUDE.md §9).

---

## 1. Rules enforced by the platform (asserted by tests)

The provider query in `providers/gcp.py` (`QUERY_TEMPLATE`) guarantees:

1. **Partition-aware** — `_PARTITIONTIME >= TIMESTAMP(@range_start) AND _PARTITIONTIME < TIMESTAMP(@range_end)` so BigQuery prunes to the requested days;
2. **Date-filtered** — `usage_start_time` is filtered identically (defence in depth);
3. **No `SELECT *`** — an explicit column whitelist;
4. **Only needed columns** — 15 columns, aggregated with `GROUP BY` at the source;
5. **Limited ranges** — `GCP_BILLING_MAX_DAYS` (default 92) ending yesterday;
6. **Row cap** — `LIMIT @max_rows` (default 100 000);
7. **Dry run first** — `dry_run=True, use_query_cache=False`, and the bytes-to-be-scanned are logged before the real query;
8. **Parameterized** — all values are `ScalarQueryParameter`s; nothing is interpolated.

These guarantees are unit-tested in `tests/test_providers_gcp.py::test_query_is_partition_aware_and_cost_guarded` and `::test_dry_run_estimates_bytes_before_querying`.

## 2. Bad vs good query examples

### ❌ Bad — full scan, unbounded

```sql
-- Scans EVERY partition, every column, every row ever exported.
SELECT * FROM `learn-cloud-gcp-506920.cloud_cost_lab_billing.gcp_billing_export_v1_012C25`;
```

```sql
-- Filters on a computed value: _PARTITIONTIME pruning does not help when the
-- predicate hides the partition column inside a function on the filtered side.
SELECT service.description, SUM(cost)
FROM `...gcp_billing_export_v1_012C25`
WHERE DATE(_PARTITIONTIME) = CURRENT_DATE()   -- function-wrapped partition column
GROUP BY 1;
```

```sql
-- Unbounded user input: a customer-supplied date range with no cap turns one
-- dashboard click into a multi-year scan.
WHERE usage_start_time >= @start AND usage_start_time <= @end
```

### ✅ Good — what the platform actually runs

```sql
SELECT
  DATE(usage_start_time) AS usage_date,
  project.id AS project_id,
  project.name AS project_name,
  service.description AS service_name,
  sku.description AS sku_description,
  resource.global_name AS resource_id,
  resource.name AS resource_name,
  location.region AS region,
  labels,
  cost,
  (SELECT IFNULL(SUM(c.amount), 0) FROM UNNEST(credits) AS c) AS credits,
  usage.amount AS usage_amount,
  usage.unit AS usage_unit,
  currency,
  billing_account_id
FROM `learn-cloud-gcp-506920.cloud_cost_lab_billing.gcp_billing_export_v1_012C25`
WHERE _PARTITIONTIME >= TIMESTAMP(@range_start)      -- partition pruning
  AND _PARTITIONTIME < TIMESTAMP(@range_end)
  AND usage_start_time >= TIMESTAMP(@range_start)    -- same bounds on the data
  AND usage_start_time < TIMESTAMP(@range_end)
GROUP BY usage_date, project_id, project_name, service_name, sku_description,
         resource_id, resource_name, region, labels, cost, credits,
         usage_amount, usage_unit, currency, billing_account_id
LIMIT @max_rows
```

with `@range_end − @range_start ≤ GCP_BILLING_MAX_DAYS` enforced in code.

## 3. Cost expectations for this project

| Operation | Data touched | Approx. cost |
| --- | --- | --- |
| Platform daily/refresh query (92-day window, 15 columns) | a few MB | **< $0.001** |
| Dry run (free) | 0 bytes scanned | $0 |
| Export storage | ~MBs; first 90 days of each partition free, then ~$0.02/GB/mo | **< $0.01/mo** for a small lab |
| Full-table scan of a 3-year export (what the guards prevent) | GBs | up to ~$0.05–0.50 per query — small, but pointless |

## 4. Retention

- The billing export keeps daily partitions indefinitely by default — for this
  lab, set a dataset-level **partition expiration** (e.g. 400 days) when
  creating the export dataset: `bq update --default_partition_expiration
  34560000 cloud_cost_lab_billing`.
- The platform's own PostgreSQL retains the mapped/ingested facts, not the raw
  export — its size is bounded by the ingestion window, not by GCP history.
- Do not retain unlimited raw data without a reason (§11).

## 5. Verification habits

- Read the dry-run log line (`bq_dry_run`) after config changes.
- `bq show --schema` after GCP changes the export schema; the mapping fails
  loudly at the boundary if columns disappear.
- If a query is ever needed outside the provider, run it as a dry run first
  and check the partition filter — then decide if the bytes are worth it.
