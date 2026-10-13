# terraform/ — Infrastructure as Code

Terraform for the **optional, real-mode** GCP resources of Cloud Cost Lab
(billing-export dataset, report bucket, read-only service account).

**Status: implemented, validated, never applied.** `terraform fmt`/`validate`
run in CI; a read-only `terraform plan` was reviewed once (5 resources to add,
per `docs/terraform.md`).
No GCP resource has been created by this repository. The platform runs fully in
`DEMO_MODE=true` without any of this (see `docs/cost-safety.md`).

## Structure

```text
terraform/
├── modules/
│   ├── iam/        read-only service account + minimal project roles (no SA keys)
│   ├── bigquery/   billing export destination dataset (table expiration = retention)
│   ├── storage/    cost-report bucket (UBLA, public access prevention, lifecycle)
│   └── compute/    optional e2-micro VM — NOT instantiated unless compute_enabled=true
└── environments/
    ├── dev/        30-day retention
    └── demo/       365-day retention
        each: main.tf  variables.tf  outputs.tf  versions.tf
              terraform.tfvars.example  backend.hcl.example  .terraform.lock.hcl
```

There is no root-level `provider.tf`/`variables.tf`: the provider is configured
per environment (`main.tf`). There are no `billing/` or `service-account/`
modules; the service account lives in `modules/iam`.

Full resource list, secure defaults and rationale: [`docs/terraform.md`](../docs/terraform.md).

## Ground rules (mandatory — CLAUDE.md §7, §51)

- `terraform fmt -check -recursive` and `terraform validate` must pass before any commit.
- **Never run `terraform apply` without a reviewed `terraform plan`** that states:
  resources created, why they are needed, billing impact, and the rollback /
  destroy method.
- No service account keys in this repository. Authentication is ADC (or
  impersonation) locally; CI uses no GCP credentials at all (a future deploy
  workflow would use Workload Identity Federation).
- `*.tfvars`, `backend.hcl`, state files and `*_override.tf` are git-ignored;
  only `*.example` templates and `.terraform.lock.hcl` are committed.

## Validate without credentials

No GCP access, no backend, no state is needed:

```bash
terraform fmt -check -recursive terraform/
for env in dev demo; do
  (cd terraform/environments/$env \
    && terraform init -backend=false -input=false \
    && terraform validate)
done
```

This is exactly what the `terraform` job in `.github/workflows/ci.yml` runs.
`init -backend=false` skips the GCS backend, so validation never touches GCS.

## Remote state (GCS backend with native locking)

Each environment declares a **partial** backend (`backend "gcs" {}`) in
`versions.tf`. The bucket name is not hardcoded; it comes from a git-ignored
`backend.hcl` at init time:

```bash
cd terraform/environments/dev            # or demo
cp backend.hcl.example backend.hcl       # set bucket; prefix is per environment
terraform init -backend-config=backend.hcl
```

**Locking.** The GCS backend locks state natively: before a state-changing
operation Terraform creates a lock object (`<prefix>/<workspace>.tflock`) with
an "object must not already exist" precondition, so a concurrent run fails
instead of corrupting state. No separate lock table or service is required.
A crashed run can leave a stale lock; release it only after confirming nobody is
running Terraform: `terraform force-unlock <LOCK_ID>`.

### Bootstrap the state bucket (once, outside Terraform)

The bucket is created manually so it does not depend on the state it stores.
These are the commands to run **when a human decides to enable remote state**;
they have not been run by this repository (flags were checked against
`gcloud ... --help`, not executed).

```bash
export PROJECT_ID="your-gcp-project-id"
export STATE_BUCKET="${PROJECT_ID}-cloud-cost-lab-tfstate"   # globally unique
export STATE_LOCATION="asia-southeast2"

# Private by construction: uniform bucket-level access + public access prevention.
gcloud storage buckets create "gs://${STATE_BUCKET}" \
  --project="${PROJECT_ID}" \
  --location="${STATE_LOCATION}" \
  --default-storage-class=STANDARD \
  --uniform-bucket-level-access \
  --public-access-prevention

# Versioning: every state write keeps the previous version (recovery path).
gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning

# Retention: drop a non-current version only when it is >= 90 days old AND at
# least 5 newer versions exist, so a rarely-changing state always keeps history.
cat > /tmp/tfstate-lifecycle.json <<'JSON'
{
  "rule": [
    {
      "action": { "type": "Delete" },
      "condition": { "isLive": false, "daysSinceNoncurrentTime": 90, "numNewerVersions": 5 }
    }
  ]
}
JSON
gcloud storage buckets update "gs://${STATE_BUCKET}" --lifecycle-file=/tmp/tfstate-lifecycle.json

gcloud storage buckets update "gs://${STATE_BUCKET}" \
  --update-labels=application=cloud-cost-lab,managed_by=manual-bootstrap
```

### Least-privilege IAM

- Use a dedicated Terraform identity (for example `terraform-runner@…`), **not**
  the read-only `cost-data-reader-*` platform identity and not a human Owner.
- Grant it `roles/storage.objectUser` **on the state bucket only** (object
  get/list/create/update/delete, which covers state and lock objects). It does
  not need bucket-admin rights. Confirm with `terraform init`; if a permission is
  reported missing, add the narrowest custom role rather than Storage Admin.
- Access it through impersonation, never a key file:
  `gcloud auth application-default login --impersonate-service-account=terraform-runner@${PROJECT_ID}.iam.gserviceaccount.com`
  (or `impersonate_service_account` in `backend.hcl`).
- Applying these environments also needs rights to create the resources
  (including project IAM bindings, which is a powerful permission). Keep that
  identity separate, short-lived and out of the running application.

```bash
gcloud storage buckets add-iam-policy-binding "gs://${STATE_BUCKET}" \
  --member="serviceAccount:terraform-runner@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectUser"
```

### Migrate existing local state to GCS

Only needed if someone already applied with local state (this repository has
not). From the environment directory, with `backend.hcl` created:

```bash
terraform init -migrate-state -backend-config=backend.hcl   # answer "yes" to copy
terraform plan                                              # must show no unexpected changes
# after verifying the remote copy, delete the local terraform.tfstate* files
```

### Cost

Estimated: a few KB per state file, so storage cost is far below one cent per
month, plus negligible operation charges. It is still a billable bucket (not
free-tier guaranteed in `asia-southeast2`); check the GCP pricing calculator
for your region. New buckets also have a default 7-day soft-delete period;
deleted objects remain billable until it expires.

### Risks

- **State is sensitive.** It can hold resource attributes and any value the
  providers return. Anyone who can read the bucket can read it. Keep the IAM
  binding minimal; do not share the bucket with unrelated projects.
- **State is critical.** Losing or corrupting it makes Terraform forget what it
  manages. Versioning is the recovery path (restore an older generation with
  `gcloud storage cp "gs://${STATE_BUCKET}/<prefix>/default.tfstate#<generation>" ...`).
- One bucket with one prefix per environment shares a blast radius; use one
  bucket per environment if dev and demo are administered by different people.
- Never store the bucket name or `backend.hcl` contents in git.

### Roll back / destroy

- **Back to local state:** add a git-ignored `backend_override.tf` containing
  `terraform { backend "local" {} }` and run
  `terraform init -migrate-state`. (Remove the override file to return to GCS.)
- **Destroy the environment first** (`terraform destroy` in each environment;
  the dataset and bucket refuse to delete non-empty unless their safety flags
  are flipped), **then** delete the state bucket last, once no environment uses it:
  `gcloud storage rm --recursive --all-versions "gs://${STATE_BUCKET}"`.
  This is irreversible: it removes every state version.

## Related

- [`docs/terraform.md`](../docs/terraform.md) — resources, validation record, security notes
- [`docs/cost-safety.md`](../docs/cost-safety.md) — the 7-question review before any billable resource
- [`docs/gcp-setup.md`](../docs/gcp-setup.md) — enabling real mode
