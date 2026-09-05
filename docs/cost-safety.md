# Cost Safety — Cloud Cost Lab

> Status: Accepted (Phase 0) · Date: 2026-09-05
> Prime directive: **Cloud Cost Lab must not become an expensive cloud project.**

This document is the safety contract for every future phase. If an action violates this document, the action is wrong — even if it is technically convenient.

---

## 1. Default posture: mock mode first

- The platform is developed and demoed with `DEMO_MODE=true` (synthetic data) by default.
- Real GCP access is opt-in, deferred to Phase 9, and never required for local development.
- Zero GCP credentials = zero cloud cost = zero risk of surprise bills.

## 2. Before creating any GCP resource — answer 7 questions

1. Is it billable?
2. What is its purpose?
3. What is the smallest practical configuration?
4. How can it be shut down?
5. How can it be destroyed?
6. What IAM permissions does it need?
7. What is the rollback path?

If any answer is unknown, the resource is not created yet.

## 3. Terraform discipline (Phase 11+)

- Before every `terraform apply`, present: resources to be created, why they are needed, potential billing impact, and the rollback/destroy method.
- `terraform apply` only after a reviewed plan. Never silently create expensive infrastructure.
- Every module documents its `terraform destroy` path.
- Prefer small resources, limited retention, and scheduled shutdown (e.g., dev compute off at night/weekends).
- State files never contain secrets; state backend access is least-privilege.

## 4. BigQuery cost protection (Phase 9+)

Billing Export tables are large. Rules:

- Never `SELECT *` on billing tables; select only required columns.
- Always filter by date/partition; aggregate early.
- Avoid repeated full-table scans; cache aggregated results in PostgreSQL.
- Use dry-run / bytes-estimate before running expensive queries; set query limits where appropriate.
- Document expensive vs optimized query pairs in `docs/bigquery-cost.md` (created in Phase 9).

## 5. Budgets and alerts

- A monthly budget with warning (70%), critical (90%), and exceeded (100%) thresholds is configured **before** any billable resource exists.
- Forecast-over-budget risk is surfaced on the dashboard, not buried in logs.
- The platform does not automatically stop production resources — budget risk triggers recommendations and human decisions.

## 6. Local environment constraints (8 GB M1 MacBook)

- Few containers at a time (default stack: api + web + postgres only).
- No local Kubernetes, no large local databases, no locally hosted LLMs.
- Cloud workloads only when the phase genuinely requires them.

## 7. Data retention

- Raw billing records are aggregated and retained with a bounded window; no unlimited raw accumulation.
- Mock/synthetic data is free and never contains real customer or billing data.

## 8. What this project will never do

- Auto-delete production resources because they "look idle".
- Modify IAM, firewall rules, databases, or Terraform state without explicit human approval and audit logging.
- Commit service account keys, credentials, or real `.env` files.
- Present uncertain forecasts as exact numbers, or potential savings as guaranteed/realized.
- Leave billable resources running without a documented shutdown path.

## 9. Per-phase safety checklist

Before declaring any phase done:

- [ ] No billable GCP resource was created without the 7-question review (§2).
- [ ] All configuration is via environment variables; `.env` is git-ignored; `.env.example` stays placeholder-only.
- [ ] Secret scan (Gitleaks pattern check) is clean for everything committed.
- [ ] Any new GCP dependency is documented with cost impact in the phase docs.
- [ ] Demo remains fully reproducible in mock mode with zero cloud cost.
