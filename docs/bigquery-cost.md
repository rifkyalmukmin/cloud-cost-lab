# BigQuery Cost Protection — Cloud Cost Lab

## Overview

BigQuery charges **$5 per TB scanned**. Billing Export tables can be large (GB-TB range). Unoptimized queries can cost real money. This document shows how to query safely.

## Cost Model

| Data Scanned | Cost |
|--------------|------|
| 10 GB | $0.05 |
| 100 GB | $0.50 |
| 1 TB | $5.00 |
| 10 TB | $50.00 |

First 1 TB per month is free (shared across all queries in the project).

## Partition Awareness

Billing Export tables are **partitioned** by `_PARTITIONDATE`.

### BAD — Scans All Partitions
```sql
SELECT 
  service.description,
  SUM(cost) as total
FROM `project.billing_export.gcp_billing_export_v1_ABC123`
GROUP BY service.description
```
**Scans:** Entire table history (potentially years of data)

### GOOD — Partition Filtered
```sql
SELECT 
  service.description,
  SUM(cost) as total
FROM `project.billing_export.gcp_billing_export_v1_ABC123`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY service.description
```
**Scans:** Only 30 days of data

**Reduction:** 90-99% cost savings for typical queries

## Column Selection

### BAD — SELECT *
```sql
SELECT * 
FROM billing_table
WHERE _PARTITIONDATE >= '2026-08-01'
```
**Scans:** All columns (100+ columns in billing export)

### GOOD — Specific Columns
```sql
SELECT 
  usage.start_time,
  project.id,
  service.description,
  cost,
  credits.amount
FROM billing_table
WHERE _PARTITIONDATE >= '2026-08-01'
```
**Scans:** Only 5 columns

**Reduction:** 95%+ cost savings

## Date Filtering

Always use **bounded** date ranges:

### BAD — Unbounded
```sql
WHERE usage.start_time > '2026-01-01'
```
Scans all data from that date forward (unbounded)

### GOOD — Bounded
```sql
WHERE _PARTITIONDATE BETWEEN '2026-08-01' AND '2026-08-31'
```
Scans exactly 31 days

### BEST — Dynamic Bounded
```sql
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  AND _PARTITIONDATE <= CURRENT_DATE()
```
Always bounded to last 90 days

## Early Aggregation

Push aggregation as early as possible:

### BAD — Late Aggregation
```sql
WITH all_records AS (
  SELECT * FROM billing_table
  WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
)
SELECT 
  project_id,
  SUM(cost)
FROM all_records
GROUP BY project_id
```
Scans and materializes all rows, then aggregates

### GOOD — Early Aggregation
```sql
SELECT 
  project.id as project_id,
  SUM(cost) as total_cost
FROM billing_table
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY project.id
```
Aggregates during scan

## Query Limits

Always use `LIMIT` for exploration:

```sql
SELECT 
  service.description,
  cost
FROM billing_table
WHERE _PARTITIONDATE = CURRENT_DATE()
ORDER BY cost DESC
LIMIT 100
```

Even with partition filter, `LIMIT` ensures the result set is bounded.

## Query Cost Estimation

Before running expensive queries, use dry-run:

```bash
bq query --dry_run --use_legacy_sql=false \
  "SELECT ... FROM billing_table WHERE ..."
```

Output shows bytes to be scanned without actually running the query.

## Cloud Cost Lab Query Patterns

### Monthly Cost Summary
```sql
SELECT 
  DATE(_PARTITIONDATE) as date,
  service.description,
  SUM(cost) as total_cost,
  SUM(IFNULL((SELECT SUM(amount) FROM UNNEST(credits)), 0)) as total_credits
FROM `{project}.{dataset}.{table}`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND project.id = @project_id
GROUP BY date, service.description
ORDER BY date, total_cost DESC
```
**Scans:** ~30 days × 4 columns = minimal

### Top Services This Month
```sql
SELECT 
  service.description,
  SUM(cost) as total_cost
FROM `{project}.{dataset}.{table}`
WHERE _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY service.description
ORDER BY total_cost DESC
LIMIT 20
```
**Scans:** Current month only, 2 columns

### Resource-Level Cost
```sql
SELECT 
  project.id,
  service.description,
  usage.resource_name,
  SUM(cost) as total_cost
FROM `{project}.{dataset}.{table}`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND project.id = @project_id
  AND cost > 0
GROUP BY project.id, service.description, usage.resource_name
HAVING total_cost > 1.0
ORDER BY total_cost DESC
LIMIT 100
```
**Scans:** 30 days, 4 columns, filtered by cost > 0

### Data Freshness Check
```sql
SELECT 
  MAX(_PARTITIONDATE) as latest_partition
FROM `{project}.{dataset}.{table}`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
```
**Scans:** Minimal (partition metadata only)

## Anti-Patterns

### ❌ SELECT * on billing tables
Scans 100+ columns unnecessarily

### ❌ No partition filter
Scans years of data

### ❌ No date upper bound
Unbounded scan

### ❌ Repeated full scans in a loop
Multiplies cost

### ❌ JOIN billing_table with itself without partition filter
Quadratic cost

### ❌ Materialized views without partition filter
Scans everything to build the view

## Cost Budgeting

For Cloud Cost Lab queries:

**Recommended monthly query budget:** $1-5

**Typical usage:**
- Daily summary query: ~10 MB scanned
- Resource inventory query: ~50 MB scanned
- Monthly report: ~100 MB scanned

**Monthly estimate:**
- 30 daily queries: 300 MB
- 10 inventory queries: 500 MB
- 4 monthly reports: 400 MB
- Total: ~1.2 GB/month → **$0.006/month** (well within free tier)

**Runaway scenario:**
- SELECT * without partition filter: 500 GB scanned → **$2.50 per query**
- 10× per day → **$750/month**

Query cost protection is **critical**.

## Implementation Checklist

Every BigQuery query in Cloud Cost Lab must:

- [ ] Filter by `_PARTITIONDATE`
- [ ] Select specific columns (never `*`)
- [ ] Use bounded date ranges (default: 90 days max)
- [ ] Apply `LIMIT` where appropriate
- [ ] Aggregate early
- [ ] Include comments explaining partition strategy
- [ ] Be tested with `--dry_run` during development
- [ ] Be documented in code with expected bytes scanned

## Query Review Template

Before merging a new BigQuery query, answer:

1. **Partition filter?** YES / NO
2. **Columns selected?** (list) / `*`
3. **Date range?** Bounded / Unbounded
4. **Estimated bytes scanned?** (MB/GB)
5. **Query cost for 30 days?** $X
6. **Annual query cost?** $X
7. **Acceptable?** YES / NO

If any answer is unacceptable, revise the query.

## Emergency Cost Control

If BigQuery costs spike:

1. **Identify expensive queries:**
   Check BigQuery → Query History → Sort by Bytes Scanned

2. **Disable the query:**
   Set `ENABLE_GCP_PROVIDER=false` or `DEMO_MODE=true`

3. **Analyze the query:**
   Review partition filter, column selection, date range

4. **Fix the query:**
   Apply partition filter, select specific columns, bound date range

5. **Re-enable with monitoring:**
   Track query cost for 24 hours before resuming normal schedule

## Resources

- [BigQuery Pricing](https://cloud.google.com/bigquery/pricing)
- [Partitioned Tables Best Practices](https://cloud.google.com/bigquery/docs/partitioned-tables)
- [Query Cost Optimization](https://cloud.google.com/bigquery/docs/best-practices-costs)
