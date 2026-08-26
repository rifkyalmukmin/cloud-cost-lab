# Runbook: BigQuery Query Failure

## Alert
BigQuery query errors in application logs

## Quick Check (< 2 minutes)

```bash
# Check API is responding
curl http://localhost:8000/health

# Check cost endpoint
curl http://localhost:8000/api/cost

# Check logs for BigQuery errors
docker logs cloud-cost-lab-api 2>&1 | grep -i "bigquery\|query failed" | tail -10
```

## Diagnosis

### 1. Is it a GCP outage?
Check: https://status.cloud.google.com/

### 2. Does the table exist?
```bash
bq show billing_export.gcp_billing_export_v1_XXXXXX
```

### 3. Are permissions correct?
```bash
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:cost-lab-reader"
```

### 4. Is it a query issue?
```bash
# Test with dry run (no cost)
bq query --dry_run --use_legacy_sql=false \
  "SELECT MAX(_PARTITIONDATE) FROM billing_export.table"
```

## Resolution

### If table renamed:
1. Find new table name: `bq ls billing_export`
2. Update GCP_BILLING_TABLE environment variable
3. Restart application

### If permissions revoked:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:cost-lab-reader@PROJECT.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
```

### If quota exceeded:
1. Check GCP Console → BigQuery → Quotas
2. Wait for quota reset (daily) or request increase

### Immediate mitigation:
Set DEMO_MODE=true to restore functionality with mock data.

## Escalation
GCP outage: monitor status page, nothing to do on our side.
