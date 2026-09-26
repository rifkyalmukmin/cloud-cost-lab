# Project Roadmap — Cloud Cost Lab

> Status: living document · Last updated: 2026-09-13
> Rule: one phase at a time. A phase is never "done" because it compiles — see Definition of Done below.

---

## 1. Phase overview

| # | Phase | Scope | Status |
| --- | --- | --- | --- |
| 0 | Planning & Foundation | Architecture, ADRs, repository structure, cost-safety & security strategy, roadmap | ✅ **Done (this commit)** |
| 1 | Local Mock Platform | FastAPI + PostgreSQL + Docker Compose + mock dataset, provider abstraction, `/health` | ✅ **Done** |
| 2 | Cost Explorer | Cost aggregation, WoW/MoM, breakdowns, filters, first dashboard pages | ✅ **Done** |
| 3 | Resource Inventory | Resources, usage series, cost↔utilization linkage | ✅ **Done** |
| 4 | Utilization Analysis | Per-metric avg/min/max/P95/stddev, cost-in-window linkage, low/high/unstable/missing evidence | ✅ **Done** |
| 5 | Recommendation Engine | Idle, oversized, disk, retention, anomaly rules; priority model; approval lifecycle | ✅ **Done** |
| 6 | Budget & Governance | Budgets with warning/critical thresholds; five advisory policies; PASS/WARNING/VIOLATION | ✅ **Done** |
| 7 | Forecasting & Anomaly | 30-day forecast (MA + linear trend) with range; rolling-average + z-score anomaly detection | ✅ **Done** |
| 8 | GCP Billing Integration | BillingDataProvider: BigQuery-backed GCP provider (partition-aware, cost-guarded), freshness, security posture | ✅ **Done (dormant in demo mode)** |
| 6 | Recommendation Engine | Idle detection, rightsizing, storage rules, lifecycle (OPEN→…→VERIFIED) | ⬜ Pending |
| 7 | Budget | Budget model, thresholds, projected month-end, budget-risk alerts | ⬜ Pending |
| 9 | Forecasting | 30-day moving average / linear regression with range | ⬜ Pending |
| 10 | Anomaly Detection | Rolling average + threshold; z-score later | ⬜ Pending |
| 11 | Savings Tracking | Potential vs realized savings with verification | ⬜ Pending |
| 11 | GCP Integration | Billing Export → BigQuery (cost-protected), real providers | ⬜ Pending |
| 12 | Monitoring / Freshness | Metrics, structured logs, SLOs, STALE/FRESH labelling | ⬜ Pending |
| 13 | Terraform | IaC for GCP resources with plan-review + destroy documentation | ⬜ Pending |
| 14 | Security | Least-privilege IAM, Secret Manager, Gitleaks/Trivy | ⬜ Pending |
| 15 | CI/CD | GitHub Actions: lint → test → build → security scan → Docker | ⬜ Pending |
| 16 | FinOps Health Score | Heuristic score: visibility, allocation, optimization, governance, forecasting, automation | ⬜ Pending |
| 17 | Reports | Daily/weekly/monthly report generation | ⬜ Pending |
| 18 | AI Advisor | Read-only AI Cloud Cost Advisor with structured context + audit log | ⬜ Pending |
| 19 | Demo Scenarios | Scripted incidents/scenarios (idle VM, spike, budget risk, …) | ⬜ Pending |
| 20 | Portfolio Preparation | README polish, screenshots, demo video, CV & interview docs | ⬜ Pending |

Milestone grouping:

- **Foundation:** 0–1 · **Core product:** 2–12 · **Cloud & hardening:** 13–16 · **FinOps depth & portfolio:** 17–20

## 2. Current phase: PHASE 8 — GCP Billing Integration (complete, dormant)

> Safety: **inspection + code + tests only** — no GCP resource was created, no terraform apply. Real data requires the manual, human-approved steps in [`docs/gcp-setup.md`](gcp-setup.md).

- Pipeline: GCP Billing Export → BigQuery → `GCPBillingProvider` → the same `BillingSnapshot` contract the mock provider satisfies; `build_providers()` selects by mode (`DEMO_MODE=true` default stays fully local).
- Query safety (§9, test-asserted): `_PARTITIONTIME` + `usage_start_time` filters, explicit column whitelist (no `SELECT *`), `GCP_BILLING_MAX_DAYS` range cap, `LIMIT` row cap, query parameters only, **dry run first** logging scanned bytes.
- Mapping: slugified services, projects, resources from `resource.global_name` (coarse `gcp_resource` type — no guessing), **unattributed billing lines become honest per-scope bucket resources**, environment strictly from the `environment` label else **UNALLOCATED** (Environment literal extended); malformed rows fail at the boundary (`GCPBillingError`).
- Security: credentials via ADC locally / WIF preferred in deployment — code never reads key files; `google-cloud-bigquery` is an optional `gcp` extra so the demo image stays light; `.gitignore` blocks service-account JSON patterns; no billing account IDs hardcoded.
- Freshness (§41): `GET /api/freshness` returns `last_updated` / `data_age_hours` / `FRESH|STALE|UNKNOWN` (threshold `FRESHNESS_MAX_HOURS`, default 48h, inclusive boundary); the Overview page renders the status chip — the demo dataset honestly reports STALE.
- Tests: 14 new (148 total) — valid/empty/error/auth-failure/malformed responses via stubbed BigQuery clients (no network, no credentials), query-safety assertions, demo-mode wiring unchanged, freshness boundaries. Docs: [`docs/gcp-billing.md`](gcp-billing.md), [`docs/bigquery-cost.md`](bigquery-cost.md), [`docs/gcp-setup.md`](gcp-setup.md), [`docs/cost-safety.md`](cost-safety.md).

## 3. Next phase: PHASE 9 — Monitoring / Data Freshness hardening (not started)

Per the user's sequencing the CLAUDE.md order shifts: next candidates are savings tracking, GCP monitoring integration, or Terraform. Entry criteria: this phase merged. **Do not start until explicitly instructed.**

## 4. Definition of Done (applies to every phase)

A feature is complete only when:

- [ ] code exists and is reviewed;
- [ ] tests exist for business logic (cost aggregation, WoW/MoM, budget %, forecast, savings math);
- [ ] validation passes (lint, tests; `terraform fmt/validate/plan` for infra);
- [ ] documentation exists and matches the implementation;
- [ ] error handling is explicit;
- [ ] security implications reviewed (no secrets, least privilege);
- [ ] cost implications considered (nothing billable created silently);
- [ ] failure mode considered and documented;
- [ ] UI/API behavior verified when applicable;
- [ ] observability added when appropriate.

## 5. Change process

New major technology or architecture change requires a new ADR in `docs/decisions/` answering: What? Why? Alternative? Trade-off? Failure mode? Security? Cost?
