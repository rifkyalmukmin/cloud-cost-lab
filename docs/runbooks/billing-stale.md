# Runbook: Billing Data Stale

## Alert
BillingDataStale (WARNING) / BillingDataCritical (CRITICAL)

## Quick Check (< 2 minutes)

```bash
# Check data freshness
curl http://localhost:8000/data-freshness

# Check API health
curl http://localhost:8000/health

# Check application logs for BigQuery errors
docker logs cloud-cost-lab-api 2>&1 | grep -i "bigquery\|billing\|error" | tail -20
```

## Diagnosis

### 1. Is GCP Billing Export still enabled?
- GCP Console → Billing → Billing Export
- Verify "Standard usage cost" export is enabled
- Note: Normal lag is ~24 hours

### 2. Can we reach BigQuery?
```bash
# If gcloud available:
bq query --dry_run "SELECT MAX(_PARTITIONDATE) FROM billing_dataset.table"
```

### 3. Are credentials valid?
```bash
# Check if GOOGLE_APPLICATION_CREDENTIALS is set and file exists
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la $GOOGLE_APPLICATION_CREDENTIALS
```

## Resolution

### If export is disabled:
1. Re-enable in GCP Console → Billing → Billing Export
2. Wait 24h for data to appear

### If credentials expired:
1. Rotate service account key
2. Update GOOGLE_APPLICATION_CREDENTIALS
3. Restart application

### If using demo mode:
Data freshness is always FRESH in demo mode. If stale:
1. Check that DEMO_MODE=true is set
2. Restart application

## Escalation
If issue persists > 4 hours: check GCP Status Dashboard for BigQuery outage.
