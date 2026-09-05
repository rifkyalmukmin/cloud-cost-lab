# terraform/ — Infrastructure as Code

Terraform for Cloud Cost Lab GCP resources.

**Status: not implemented yet (Phase 11).** No `.tf` files exist — only this plan. Creating cloud resources before the application needs them would violate the project's cost-safety rules (`docs/cost-safety.md`).

## Planned structure

```text
terraform/
├── modules/
│   ├── billing/          Billing export helpers (where applicable)
│   ├── bigquery/         Billing export dataset with limited retention
│   ├── service-account/  Least-privilege read-only service accounts
│   ├── storage/          Storage with lifecycle/retention rules
│   └── compute/          Small demo compute (only when justified)
├── environments/
│   ├── dev/
│   └── demo/
├── provider.tf
├── variables.tf
└── outputs.tf
```

## Ground rules (mandatory)

- `terraform fmt -check` and `terraform validate` must pass before any commit.
- `terraform apply` only after a reviewed `terraform plan` that shows: resources created, why, billing impact, and rollback/destroy method.
- Every module documents its `terraform destroy` path.
- Prefer the smallest practical configuration, limited retention, and scheduled shutdown.
- No service account keys in this repository — ever.
