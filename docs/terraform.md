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
cp backend.hcl.example backend.hcl             # then set the state bucket (§3.1)
terraform init -backend-config=backend.hcl     # downloads the provider, wires remote state
terraform plan                                  # review: resources + cost
terraform apply                                 # HUMAN decision only
```

- **Credentials** are never in code: ADC (or service-account impersonation)
  locally; CI uses no GCP credentials, and a future deploy workflow would use
  Workload Identity Federation. `*.tfvars` and `backend.hcl` are git-ignored
  while `terraform.tfvars.example` / `backend.hcl.example` are committed.
- **Destroy**: `terraform destroy` per environment. The dataset and bucket
  refuse to delete non-empty unless their safety flags are explicitly
  flipped — an extra human checkpoint before billing history disappears.
- **Lock file**: `.terraform.lock.hcl` is committed for reproducible provider
  versions.
- **Credential-free validation** (what CI runs): `terraform init -backend=false
  && terraform validate` — no GCS access needed.

### 3.1 Remote state (GCS backend)

Each environment declares `backend "gcs" {}` (partial configuration) in
`versions.tf`; the bucket name is supplied through `backend.hcl`, so it is
never hardcoded or committed.

| Topic | Decision |
| --- | --- |
| Backend | `gcs` — supports **native state locking** (a lock object is created with an "object must not exist" precondition, so concurrent runs fail instead of corrupting state); no lock table/service to run |
| Why not local state | a single laptop copy is lost/corrupted easily and cannot be shared or locked across machines or CI |
| Why not a Terraform-managed bucket | the state bucket would depend on the state it stores; it is bootstrapped once, manually |
| Bucket hardening | uniform bucket-level access, public access prevention, object versioning, lifecycle that deletes non-current versions only when ≥ 90 days old **and** ≥ 5 newer versions exist |
| Access | dedicated Terraform identity with `roles/storage.objectUser` on the state bucket only, used via impersonation — never a key file, never the read-only platform identity |
| Cost (estimated) | KBs of data: well under one cent per month, still billable; default 7-day soft-delete applies |
| Per-environment isolation | one `prefix` per environment (`cloud-cost-lab/dev`, `cloud-cost-lab/demo`) |
| Failure modes | stale lock after a crashed run → `terraform force-unlock <ID>` (only after confirming nobody is applying); corrupted/overwritten state → restore a previous object generation from versioning; bucket deleted → state lost (hence the destroy-order rule) |
| Security | **state is sensitive** (resource attributes, provider-returned values); anyone with read access to the bucket can read it |

Bootstrap commands, IAM binding, local→GCS migration
(`terraform init -migrate-state -backend-config=backend.hcl`), rollback to
local state and bucket destroy order are in
[`terraform/README.md`](../terraform/README.md#remote-state-gcs-backend-with-native-locking).
Those commands are documentation only: no bucket has been created and the GCS
backend has not been exercised against real GCP from this repository (only
`init -backend=false` + `validate` were run).

## 4. Validation performed (Phase 10)

```text
terraform fmt -recursive           # clean (formatting fixes applied once)
terraform validate (demo, dev)     # Success! The configuration is valid.
terraform plan (demo, real project via ADC)
  Plan: 5 to add, 0 to change, 0 to destroy.
```

No `-out` plan file was kept and no `apply` was executed.

### Remote-state hardening check (partial GCS backend)

After adding `backend "gcs" {}` (partial configuration) to both environments:

```text
terraform fmt -check -recursive terraform/           # clean
terraform init -backend=false && terraform validate   # dev, demo: Success!
terraform init (no backend config, non-interactive)   # fails as intended: bucket must be supplied
terraform init + local backend_override.tf + validate # works (local-only escape hatch)
```

Run with Terraform 1.16.4 on a scratch copy of the repository (CI pins 1.9.8 and
runs the same `-backend=false` commands). Provider lock files were unchanged. No
GCS bucket exists, so `init -backend-config=backend.hcl`, locking and
`-migrate-state` against real GCS were **not** exercised; no plan/apply was run.

## 5. Security notes

- Least privilege throughout: project-level IAM limited to `jobUser`;
  data-level READER grants scoped to the specific dataset/bucket.
- No secrets, no SA keys, no project IDs hardcoded (variables only).
- All resources carry `managed_by=terraform`, `application=cloud-cost-lab`,
  `environment=<env>` labels — which the platform's own REQUIRE_* policies
  would then verify.
- State may contain resource metadata and provider-returned values, so it is
  sensitive: keep local state out of git (`*.tfstate*` is git-ignored), and use
  the GCS backend (versioned, private, least-privilege access) for shared use.
