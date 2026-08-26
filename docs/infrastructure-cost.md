# Infrastructure Cost — Cloud Cost Lab

## Principle

Cloud Cost Lab must not become an expensive project. Every infrastructure resource is chosen to minimize cost while providing required functionality.

## Cost Breakdown

### Minimal Setup (Dev — No Compute)

| Resource | Configuration | Monthly Cost |
|----------|--------------|-------------|
| Service accounts (2x) | IAM only | $0.00 |
| BigQuery dataset | Empty (export adds data) | $0.00 |
| BigQuery storage | ~1 GB billing data | $0.02 |
| BigQuery queries | ~5 GB scanned/month | $0.025 |
| Cloud Storage | ~100 MB reports | $0.002 |
| **Total** | | **~$0.05/month** |

### Standard Setup (Dev — With Compute)

| Resource | Configuration | Monthly Cost |
|----------|--------------|-------------|
| All of above | | $0.05 |
| e2-micro (preemptible) | 0.25 vCPU, 1GB RAM | $3.50 |
| Boot disk (10GB standard) | pd-standard | $0.40 |
| **Total** | | **~$4.00/month** |

### Production Setup (If Deployed)

| Resource | Configuration | Monthly Cost |
|----------|--------------|-------------|
| e2-small (non-preemptible) | 0.5 vCPU, 2GB RAM | $13.00 |
| Boot disk (20GB SSD) | pd-ssd | $3.40 |
| Cloud SQL (db-f1-micro) | Smallest instance | $7.67 |
| Cloud Storage | 1 GB reports | $0.02 |
| BigQuery queries | ~10 GB/month | $0.05 |
| Load balancer | If needed | $18.00 |
| **Total** | | **~$42/month** |

## Cost Controls

### Built-In

1. **Preemptible instances** for non-production (70% cheaper)
2. **e2-micro** machine type (smallest available)
3. **pd-standard** disk (cheapest persistent disk)
4. **Lifecycle policies** on storage (auto-delete after 90 days)
5. **Table expiration** on BigQuery datasets (365 days)
6. **No external IP** by default (saves static IP cost)

### Operational

1. **DEMO_MODE=true** as default (zero GCP cost)
2. **terraform plan** before any apply (review cost)
3. **terraform destroy** documented for every resource
4. **Budget alerts** configured separately in GCP Console
5. **Query cost protection** in application code (see bigquery-cost.md)

## Monthly Budget Recommendation

| Environment | Budget | Alert At |
|-------------|--------|----------|
| Demo (mock only) | $0 | N/A |
| Dev (minimal) | $5 | $3 |
| Dev (with compute) | $10 | $7 |
| Production | $50 | $35 |

## Scaling Cost

If the project scales:

| Scaling Factor | Cost Impact |
|---------------|-------------|
| More BQ queries | $5/TB scanned |
| Larger instance | $13-50/month per tier |
| Cloud SQL | $8-50/month per tier |
| Multiple environments | 2-3× base cost |
| HA (redundancy) | 2× compute cost |

## Cost Optimization Applied

This project practices what it preaches:

1. **Smallest practical instances** — e2-micro, not e2-standard
2. **Preemptible where possible** — dev workloads tolerate interruption
3. **Auto-expiring data** — lifecycle rules prevent unbounded growth
4. **Bounded queries** — partition filters prevent expensive scans
5. **No unnecessary resources** — demo environment has IAM only
6. **Infrastructure off by default** — demo mode needs zero GCP

## Destroy Procedure

Complete teardown:

```bash
# Dev environment
cd terraform/environments/dev
terraform destroy -auto-approve

# Demo environment
cd terraform/environments/demo
terraform destroy -auto-approve

# Verify nothing remains
gcloud iam service-accounts list --filter="displayName:Cloud Cost Lab"
bq ls
gsutil ls
```

After destroy:
- Set `DEMO_MODE=true` in application
- Application continues working with mock data
- Zero monthly cost
