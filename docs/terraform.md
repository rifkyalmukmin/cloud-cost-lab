# Terraform — GCP Infrastructure as Code (Phase 10)

> Status: Implemented (validated; NOT applied) · Date: 2026-09-13
> Modules for the platform's real-mode infrastructure: **iam**, **bigquery**, **storage**, **compute**; environments **dev** and **demo**.
> `terraform plan` was executed read-only against the real project (5 to add, 0 destroy). **`terraform apply` has never been run** — enabling real infrastructure is an explicit human decision (CLAUDE.md §7, §51).

---

## 1. Repository layout

```text
terraform/
├── modules/
│   ├── iam/         # read-only service account (+ minimal project roles)
│   ├── bigquery/    # billing export destination dataset
│   ├── storage/     # cost-report archive bucket
│   └── compute/     # optional e2-micro VM (NOT instantiated by default)
└── environments/
    ├── dev/         # 30-day retention, compute disabled
    └── demo/        # 365-day retention, compute disabled
```

Every module follows the same shape: `versions.tf` (pinned provider `~> 6.0`),
`variables.tf` (documented, typed, secure defaults), `main.tf` (small), `outputs.tf`.

## 2. What gets created (the full plan: 5 resources)

| Resource | Purpose | Secure defaults |
| --- | --- | --- |
| Service account `cost-data-reader-<env>` | read-only platform identity | no key is created (ADC/WIF only, §36) |
| `google_project_iam_member` `roles/bigquery.jobUser` | run queries | single role; data-level grants live on the resources |
| BigQuery dataset `cloud_cost_lab_billing_<env>` | billing export destination | table expiration (= retention), dataset-only READER grants, `delete_contents_on_destroy = false` |
| GCS bucket `cloud-cost-lab-reports-<env>` | generated cost reports | `uniform_bucket_level_access`, `public_access_prevention = "enforced"`, versioning, lifecycle deletion at retention, `force_destroy = false` |
| Bucket IAM `objectViewer` for the SA | read reports | bucket-scoped, not project-scoped |

**Compute is deliberately not provisioned**: the platform runs on the
developer machine, and §7 forbids unneeded billable infrastructure. The
`compute` module exists for a future, deliberate deployment (e2-micro, no
public IP, shielded boot, os-login, read-only scopes) and both environments
instantiate it with `count = var.compute_enabled ? 1 : 0` (`false`).

## 3. Usage

```bash
cd terraform/environments/demo
cp terraform.tfvars.example terraform.tfvars   # then set gcp_project_id
terraform init                                  # downloads the provider
terraform plan                                  # review: resources + cost
terraform apply                                 # HUMAN decision only
```

- **State** is local by default; each environment ships a commented GCS
  backend block (create the state bucket manually — it stays outside
  Terraform so its own state never bootstraps itself).
- **Credentials** are never in code: ADC locally, Workload Identity
  Federation in deployment; `*.tfvars` is git-ignored while
  `terraform.tfvars.example` is committed.
- **Destroy**: `terraform destroy` per environment. The dataset and bucket
  refuse to delete non-empty unless their safety flags are explicitly
  flipped — an extra human checkpoint before billing history disappears.
- **Lock file**: `.terraform.lock.hcl` is committed for reproducible provider
  versions.

## 4. Validation performed (Phase 10)

```text
terraform fmt -recursive           # clean (formatting fixes applied once)
terraform validate (demo, dev)     # Success! The configuration is valid.
terraform plan (demo, real project via ADC)
  Plan: 5 to add, 0 to change, 0 to destroy.
```

No `-out` plan file was kept and no `apply` was executed.

## 5. Security notes

- Least privilege throughout: project-level IAM limited to `jobUser`;
  data-level READER grants scoped to the specific dataset/bucket.
- No secrets, no SA keys, no project IDs hardcoded (variables only).
- All resources carry `managed_by=terraform`, `application=cloud-cost-lab`,
  `environment=<env>` labels — which the platform's own REQUIRE_* policies
  would then verify.
- State may contain resource metadata: keep local state out of git; use the
  GCS backend with versioning for shared use.
