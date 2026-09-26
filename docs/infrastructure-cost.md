# Infrastructure Cost — Cloud Cost Lab

> Status: Documented · Date: 2026-09-13
> Expected monthly cost of the infrastructure this repository's Terraform can create (Phase 10), with the current monthly platform spend context (CLAUDE.md §7: Cloud Cost Lab must not become an expensive cloud project).

---

## 1. Current platform spend (demo dataset)

The demo dataset simulates roughly **$20/month** (June $18 → September run-rate
~$26; the analysis window sums to ~$60 over 97 days). That is the *modelled*
GCP spend the platform analyses — the platform itself costs nothing while it
runs locally in demo mode.

## 2. Terraform-managed resources (demo or dev environment)

| Resource | Billing driver | Free tier cover | Expected monthly cost |
| --- | --- | --- | --- |
| BigQuery dataset `cloud_cost_lab_billing_<env>` | storage of export partitions (active storage free ≤ 10 GB/dataset), queries $5/TB scanned | a lab export is MBs; platform queries scan MBs | **~$0** |
| GCS bucket `cloud-cost-lab-reports-<env>` | object storage ~$0.02/GB/mo, lifecycle deletes at retention (30d dev / 365d demo) | 5 GB free | **~$0** (a few MB of reports) |
| Service account + IAM bindings | free | — | **$0** |
| Compute instance (only if `compute_enabled=true`) | e2-micro ≈ $6.7/mo + ~$1 disk; 1 free e2-micro/month in us-west1 only | partially | **$0 by default** — deliberately not provisioned |

**Worst case for this repository's defaults: ~$0–1/month.** The only realistic
cost lever is keeping large exports long-term — countered by the dataset
table expiration (30/365 days) and bucket lifecycle rules.

## 3. Cost guardrails built into the IaC

- `default_table_expiration_days` — billing history auto-expires (retention,
  §9/§11); no unbounded raw data retention.
- Bucket `lifecycle_rule` deletes objects past `object_retention_days`.
- `e2-micro` as the compute default (§7: smallest practical configuration),
  and the instance is not created at all unless flipped explicitly.
- No NAT gateway, no load balancer, no managed instance group — the classic
  silent bill generators are absent by design.

## 4. Cost risks to watch (the honest list)

- **BigQuery queries** — $5/TB scanned. The platform's queries are
  partition-filtered and MB-sized (see `docs/bigquery-cost.md`), but ad-hoc
  console queries are the usual surprise. Keep the dry-run habit.
- **Ops Agent** — if a future VM runs it, ingest logs/trace costs can apply
  beyond the free allotment (50 MiB for logs, traces billed separately).
- **Public IP on a VM** — off by default in the compute module; NAT-less
  private access needs care, and leaving a default-VM running still costs
  disk even if stopped.
- **Multiple environments** — dev and demo each create their own dataset +
  bucket; destroy environments that are not in use.

## 5. Monitoring the spend

- The platform's own budget feature (Phase 6) can watch the real billing
  export once real mode is enabled — `$50/month` with 70/90 thresholds is the
  seeded example.
- Cloud Billing budget alerts (console-side, free) complement it: set one at
  $10 to catch surprises early.
