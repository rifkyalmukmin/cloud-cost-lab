# GCP Setup Guide — Cloud Cost Lab

## Prerequisites

- GCP account with billing enabled
- `gcloud` CLI installed
- A project with Billing Export enabled

## Step 1: Install gcloud CLI

```bash
# macOS
brew install --cask google-cloud-sdk

# Verify
gcloud version
```

## Step 2: Authenticate

```bash
gcloud auth login
gcloud auth application-default login
```

## Step 3: Enable Billing Export

1. Open GCP Console → Billing → Billing Export
2. Select project or create new one for billing data
3. Enable "Standard usage cost" export to BigQuery
4. Note the dataset name (e.g., `billing_export`)
5. Note the table name (e.g., `gcp_billing_export_v1_ABC123DEF456`)

**Important:** Billing Export only starts recording from the moment it's enabled. Historical data before enable date is not available.

## Step 4: Create Service Account

```bash
export PROJECT_ID="your-project-id"

# Create service account
gcloud iam service-accounts create cost-lab-reader \
    --display-name="Cloud Cost Lab Reader" \
    --project=$PROJECT_ID

# Grant BigQuery data viewer (read billing data)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cost-lab-reader@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer"

# Grant BigQuery job user (run queries)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cost-lab-reader@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"
```

## Step 5: Generate Key (Local Development Only)

```bash
gcloud iam service-accounts keys create /tmp/cost-lab-key.json \
    --iam-account=cost-lab-reader@${PROJECT_ID}.iam.gserviceaccount.com

# Move to secure location (NEVER commit this file)
mv /tmp/cost-lab-key.json ~/.config/cloud-cost-lab/key.json
```

**Security Note:** For production, prefer Workload Identity Federation over JSON keys.

## Step 6: Configure Environment

```bash
# .env (never commit this file)
DEMO_MODE=false
GCP_BILLING_PROJECT=your-project-id
GCP_BILLING_DATASET=billing_export
GCP_BILLING_TABLE=gcp_billing_export_v1_ABC123DEF456
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

## Step 7: Install Python Dependencies

```bash
cd apps/api
source .venv/bin/activate
pip install google-cloud-bigquery
```

## Step 8: Verify

```bash
# Start API
uvicorn app.main:app --port 8000

# Check provider
curl http://localhost:8000/ready
# Should return: {"status": "ready", "provider": "gcp", "data_loaded": true}

# Check freshness
curl http://localhost:8000/data-freshness
# Should return: {"status": "FRESH", "last_updated": "...", "data_age_hours": ...}
```

## Permissions Summary

| Role | Purpose | Required |
|------|---------|----------|
| bigquery.dataViewer | Read billing export tables | YES |
| bigquery.jobUser | Run BigQuery queries | YES |
| billing.viewer | View billing account | NO (optional) |
| monitoring.viewer | Read metrics | NO (future Phase 10) |

## Cost Implications

| Resource | Cost | When |
|----------|------|------|
| BigQuery queries | $5/TB scanned | Each API refresh |
| Service account | Free | Always |
| Billing Export | Free | Always (GCP feature) |

**Expected monthly cost:** $0.01-$0.10 (typical 30-day queries scan ~1-10 GB)

See [docs/bigquery-cost.md](bigquery-cost.md) for query optimization.

## Destroy / Disable

### Disable Integration (keep resources)
```bash
# Set demo mode in .env
DEMO_MODE=true
```

### Remove Service Account
```bash
gcloud iam service-accounts delete \
    cost-lab-reader@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=$PROJECT_ID
```

### Remove Key File
```bash
rm ~/.config/cloud-cost-lab/key.json
```

### Disable Billing Export
Navigate to GCP Console → Billing → Billing Export → Disable

## Workload Identity Federation (Production)

For GCP-hosted deployments (Cloud Run, GKE), prefer Workload Identity Federation over JSON keys:

```bash
# No JSON keys needed — identity is based on the running workload
gcloud run services update cloud-cost-lab-api \
    --service-account=cost-lab-reader@${PROJECT_ID}.iam.gserviceaccount.com
```

Benefits:
- No key rotation needed
- No key file to protect
- Identity tied to workload, not a file
- Automatic credential management

## Troubleshooting

### "google-cloud-bigquery not installed"
```bash
pip install google-cloud-bigquery
```

### "Failed to initialize BigQuery client"
- Check GOOGLE_APPLICATION_CREDENTIALS path
- Verify service account exists
- Verify project ID is correct

### "BigQuery query failed"
- Check GCP_BILLING_TABLE name (may have changed)
- Verify bigquery.dataViewer and bigquery.jobUser roles
- Check if billing export is enabled

### Data freshness is STALE
- Billing Export has ~24h lag — this is normal
- If > 48h stale, check if export is still enabled
- Check BigQuery for errors in the export job

### Data freshness is UNKNOWN
- Cannot connect to BigQuery
- Check authentication
- Check network connectivity to GCP
