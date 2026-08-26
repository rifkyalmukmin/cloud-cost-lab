# ADR-004: GCP Integration Strategy

## Status
Accepted

## Context
Cloud Cost Lab needs real billing and utilization data from Google Cloud Platform. We must decide:
- How to access billing data
- How to access utilization metrics
- How to authenticate
- How to protect against accidental cost

## Decision

### Billing Data: BigQuery Billing Export
GCP provides Billing Export to BigQuery — a daily export of all billing line items into a BigQuery dataset.

Configuration:
```
GCP_BILLING_PROJECT — project containing the billing dataset
GCP_BILLING_DATASET — dataset name
GCP_BILLING_TABLE   — table name (standard or detailed export)
```

### Utilization Data: Cloud Monitoring API
CPU, memory, disk, and network metrics accessed via Cloud Monitoring (Stackdriver) API.

### Authentication: Service Accounts + Workload Identity Federation
- Local development: service account key (stored securely, never committed)
- CI/CD: Workload Identity Federation (keyless)
- Production: Workload Identity or attached service account

### Cost Protection
- Partition-filtered queries only
- Column selection (never SELECT *)
- Query byte estimation before execution
- Bounded date ranges
- Rate limiting on data collection schedule

## Alternatives Considered

### Cloud Billing API (not BigQuery)
- Pro: Real-time, no BigQuery cost
- Con: Limited historical data, less flexible queries, paginated
- Verdict: BigQuery export provides richer data and SQL flexibility

### Export to Cloud Storage (CSV)
- Pro: No BigQuery query cost
- Con: No SQL, harder to analyze, stale files
- Verdict: BigQuery is the standard approach for billing analytics

### Prometheus for utilization
- Pro: Standard metrics store
- Con: Requires running Prometheus, scraping config, extra infrastructure
- Verdict: Cloud Monitoring is native, no extra infra, free tier sufficient

## Trade-offs
- BigQuery queries cost money (per byte scanned) — mitigated by partition filters and bounded queries
- Billing Export has ~24h lag — acceptable for cost analytics (not real-time)
- Service account keys are a security risk — mitigated by least-privilege roles and Workload Identity Federation for CI
- Cloud Monitoring API has quota limits — mitigated by batching and caching

## Consequences
- Application requires two GCP permissions: BigQuery read + Monitoring read
- Separate service accounts: `cost-data-reader` and `monitoring-reader`
- BigQuery cost documented in `docs/cost-safety.md`
- Data freshness tracked and displayed in dashboard
- Fallback to demo mode if GCP is unavailable
