# Terraform — Cloud Cost Lab

## Overview

Infrastructure as Code for Cloud Cost Lab using Terraform. Manages GCP service accounts, BigQuery datasets, Cloud Storage buckets, and (optionally) compute instances.

## Structure

```
terraform/
├── modules/
│   ├── iam/         # Service accounts (cost-reader, monitoring-reader)
│   ├── bigquery/    # Billing export dataset
│   ├── storage/     # Reports bucket
│   └── compute/     # API server instance (optional)
└── environments/
    ├── dev/         # Development (IAM + BigQuery + Storage)
    └── demo/        # Demo (IAM only, minimal)
```

## Modules

### IAM Module
Creates least-privilege service accounts:
- `cost-reader`: BigQuery data viewer + job user
- `monitoring-reader`: Cloud Monitoring viewer

No Owner, Editor, or Admin roles.

### BigQuery Module
Creates a dataset for billing export with:
- Table expiration (default: 365 days)
- Reader access for cost-reader service account
- Location matching project region

### Storage Module
Creates a reports bucket with:
- Uniform bucket-level access
- Public access prevention enforced
- Lifecycle rule (auto-delete after retention period)
- Reader access for cost-reader service account

### Compute Module (Optional)
Creates a minimal API server instance:
- e2-micro (smallest available)
- Container-Optimized OS
- Preemptible for non-production
- No external IP by default
- OS Login enabled

## Usage

### Prerequisites

1. Install Terraform >= 1.5
2. Authenticate: `gcloud auth application-default login`
3. Copy tfvars: `cp terraform.tfvars.example terraform.tfvars`
4. Fill in project_id

### Commands

```bash
cd terraform/environments/dev

# Format check
terraform fmt -check -recursive

# Initialize
terraform init

# Validate syntax
terraform validate

# Plan (review BEFORE applying)
terraform plan -out=tfplan

# REVIEW THE PLAN CAREFULLY
# Check: resources, cost, permissions

# Apply (only after review)
terraform apply tfplan

# Destroy (removes all resources)
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

### CRITICAL: Before Apply

Always review the plan output and verify:

1. **Resources to create** — are they all needed?
2. **Potential cost** — what will this cost monthly?
3. **Security** — what permissions are granted?
4. **Destroy path** — how to remove everything?

## Cost Estimate (Dev Environment)

| Resource | Monthly Cost |
|----------|-------------|
| Service accounts (2x) | Free |
| BigQuery dataset (empty) | Free |
| BigQuery storage (per GB) | $0.02/GB |
| Cloud Storage bucket | $0.02/GB |
| **Total (no compute)** | **~$0.10/month** |

If compute module is added:
| Resource | Monthly Cost |
|----------|-------------|
| e2-micro (preemptible) | ~$3.50/month |
| 10GB pd-standard disk | ~$0.40/month |
| **Total with compute** | **~$4.00/month** |

## Security

### Secrets

**NEVER commit:**
- `terraform.tfvars` (contains project ID)
- `*.tfstate` (contains infrastructure state)
- `*.tfstate.backup`
- Service account keys

All are covered by `.gitignore`.

### IAM Principle of Least Privilege

- cost-reader: read billing data only
- monitoring-reader: read metrics only
- No write/delete permissions on any resource
- No billing admin access
- No project-level editor/owner

### Network Security

- Compute instances: no external IP by default
- Storage: public access prevention enforced
- BigQuery: dataset-level access control

## Destroy Strategy

### Remove All Resources
```bash
cd terraform/environments/dev
terraform destroy
```

### Remove Specific Module
```bash
terraform destroy -target=module.compute
```

### Emergency: Manual Cleanup
If Terraform state is corrupted:
```bash
gcloud iam service-accounts delete cloud-cost-lab-cost-reader@PROJECT.iam.gserviceaccount.com
gcloud iam service-accounts delete cloud-cost-lab-mon-reader@PROJECT.iam.gserviceaccount.com
bq rm -r -f billing_export
gsutil rm -r gs://PROJECT-cloud-cost-lab-reports/
```

## Environments

### Dev
Full setup: IAM + BigQuery + Storage. Use for development with real GCP billing data.

### Demo
Minimal: IAM only. Use for demo/testing when you only need service accounts configured.

## Validation Checklist

Before merging Terraform changes:

- [ ] `terraform fmt -check` passes
- [ ] `terraform validate` passes
- [ ] `terraform plan` reviewed
- [ ] Cost implications documented
- [ ] Security implications reviewed
- [ ] Destroy path documented
- [ ] No secrets in committed files
