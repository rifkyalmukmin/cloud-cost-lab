# GCP Billing Integration — Cloud Cost Lab

## Overview

Cloud Cost Lab integrates with GCP Billing Export to analyze real cloud costs. **Demo mode (mock data) is the default** — GCP integration is opt-in for users with access to billing data.

## Architecture

```
GCP Billing Account
        ↓
  Billing Export
        ↓
  BigQuery Dataset
        ↓
  gcp_billing_export_v1_XXXXXX (table)
        ↓
  GCPBillingProvider
        ↓
  Cloud Cost Lab
```

## Provider Abstraction

```python
class BillingDataProvider(ABC):
    @abstractmethod
    def get_cost_records(start_date, end_date) -> List[CostRecord]
    
    @abstractmethod
    def get_data_freshness() -> DataFreshness

# Implementations
MockBillingProvider  # default, no GCP needed
GCPBillingProvider   # requires GCP billing export
```

## Requirements

### 1. Billing Export Setup

Enable Billing Export in GCP Console:
1. Navigation → Billing → Billing Export
2. Enable BigQuery Export
3. Select/create dataset (e.g., `billing_export`)
4. Note the table name: `gcp_billing_export_v1_XXXXXX`

### 2. Service Account

Create a service account with **read-only** permissions:

```bash
gcloud iam service-accounts create cost-lab-reader \
    --display-name="Cloud Cost Lab Reader"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:cost-lab-reader@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:cost-lab-reader@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"
```

**Permissions needed:**
- `bigquery.dataViewer` — read billing data
- `bigquery.jobUser` — run queries

**Permissions NOT needed:**
- Owner
- Editor
- Billing Administrator
- Any write permissions

### 3. Environment Variables

```bash
# Enable GCP mode
DEMO_MODE=false

# BigQuery billing export location
GCP_BILLING_PROJECT=my-billing-project
GCP_BILLING_DATASET=billing_export
GCP_BILLING_TABLE=gcp_billing_export_v1_ABC123

# Authentication
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

## Data Freshness

Billing Export has ~24-hour lag. Cloud Cost Lab tracks freshness:

| Status | Condition |
|--------|-----------|
| **FRESH** | Data age < 36 hours |
| **STALE** | Data age ≥ 36 hours |
| **UNKNOWN** | Cannot determine freshness |

Dashboard displays:
- Last updated timestamp
- Data age
- Freshness status

Never present stale data as current without indication.

## Query Safety

See [bigquery-cost.md](bigquery-cost.md) for query cost protection.

All queries MUST:
- Filter by partition (`_PARTITIONDATE`)
- Select specific columns (never `SELECT *`)
- Limit date ranges (default: 90 days)
- Use LIMIT where appropriate
- Aggregate early

## Switching Between Providers

```python
# Automatic based on DEMO_MODE
if settings.demo_mode:
    provider = MockBillingProvider()
else:
    provider = GCPBillingProvider(
        project=settings.gcp_billing_project,
        dataset=settings.gcp_billing_dataset,
        table=settings.gcp_billing_table,
    )
```

## Cost Considerations

### BigQuery Query Cost

Billing Export tables can be **large** (millions of rows).

**BAD** query (scans all data):
```sql
SELECT * FROM `billing_export.gcp_billing_export_v1_ABC123`
```
Cost: scans entire table (potentially GB+)

**GOOD** query (partition-filtered):
```sql
SELECT
  service.description,
  SUM(cost) as total_cost
FROM `billing_export.gcp_billing_export_v1_ABC123`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND project.id = 'my-project'
GROUP BY service.description
LIMIT 100
```
Cost: scans ~30 days only

### Cloud Cost Lab Self-Cost

Running Cloud Cost Lab on GCP incurs cost:
- BigQuery queries: $5/TB scanned
- Cloud Run/Compute instances
- Cloud SQL database
- Cloud Storage
- Monitoring/Logging

**Estimate monthly cost:**
- Development: $5-20/month
- Production with monitoring: $20-50/month

See [docs/cost-safety.md](cost-safety.md) for cost protection rules.

## Security

**NEVER commit:**
- Service account JSON keys
- Billing account IDs
- Project IDs (if sensitive)
- BigQuery credentials
- Any secrets

Use:
- Environment variables
- Secret Manager
- Workload Identity Federation (preferred for GCP-hosted deployments)

## Testing Real Integration

Before going to production:

1. **Validate export exists:**
   ```bash
   bq ls billing_export
   bq show billing_export.gcp_billing_export_v1_ABC123
   ```

2. **Test small query:**
   ```bash
   bq query --use_legacy_sql=false --max_rows=5 \
     "SELECT _PARTITIONDATE, service.description, cost 
      FROM billing_export.gcp_billing_export_v1_ABC123 
      WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
      LIMIT 5"
   ```

3. **Check query cost:**
   Query billing console or use `--dry_run` to estimate bytes scanned

4. **Monitor freshness:**
   Check `_PARTITIONDATE` max value vs current date

## Rollback

To disable GCP integration:

```bash
# .env
DEMO_MODE=true
```

Mock provider resumes immediately. No data loss.

## Limitations

- Billing Export has ~24h lag (not real-time)
- Multi-project aggregation requires cross-project permissions
- Credit allocations may not be reflected immediately
- Sub-resource allocation requires labels/tags
- BigQuery query costs accumulate with frequent refreshes
