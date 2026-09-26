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
| 9 | GCP Monitoring Integration | MonitoringDataProvider: Cloud Monitoring metrics, connections metric, evidence-strengthened rules | ✅ **Done (dormant in demo mode)** |
| 6 | Recommendation Engine | Idle detection, rightsizing, storage rules, lifecycle (OPEN→…→VERIFIED) | ⬜ Pending |
| 7 | Budget | Budget model, thresholds, projected month-end, budget-risk alerts | ⬜ Pending |
| 9 | Forecasting | 30-day moving average / linear regression with range | ⬜ Pending |
| 10 | Anomaly Detection | Rolling average + threshold; z-score later | ⬜ Pending |
| 14 | Savings Tracking | Potential vs realized savings with verification | ⬜ Pending |
| 11 | GCP Integration | Billing Export → BigQuery (cost-protected), real providers | ⬜ Pending |
| 15 | Monitoring / Freshness | Metrics, structured logs, SLOs, STALE/FRESH labelling | ⬜ Pending |
| 16 | Terraform | IaC for GCP resources with plan-review + destroy documentation | ⬜ Pending |
| 17 | Security | Least-privilege IAM, Secret Manager, Gitleaks/Trivy | ⬜ Pending |
| 18 | CI/CD | GitHub Actions: lint → test → build → security scan → Docker | ⬜ Pending |
| 19 | FinOps Health Score | Heuristic score: visibility, allocation, optimization, governance, forecasting, automation | ⬜ Pending |
| 20 | Reports | Daily/weekly/monthly report generation | ⬜ Pending |
| 21 | AI Advisor | Read-only AI Cloud Cost Advisor with structured context + audit log | ⬜ Pending |
| 22 | Demo Scenarios | Scripted incidents/scenarios (idle VM, spike, budget risk, …) | ⬜ Pending |
| 23 | Portfolio Preparation | README polish, screenshots, demo video, CV & interview docs | ⬜ Pending |

Milestone grouping:

- **Foundation:** 0–1 · **Core product:** 2–12 · **Cloud & hardening:** 13–17 · **FinOps depth & portfolio:** 18–21

## 2. Current phase: PHASE 13 — Savings Tracking (complete)

- **Lifecycle** (CLAUDE.md §23): OPEN → APPROVED → IMPLEMENTED → VERIFIED, REJECTED branch. Transitions enforced per source status (`409` otherwise): `POST /{id}/implement` records `implemented_at` (backfillable), `POST /{id}/verify` computes **realized savings from actual data**.
- **Before/after calculation:** 30-day net-cost daily averages around the implementation date (≥ 7 after-days required); realized = monthly-equivalent difference; **negative realized stored as measured**; insufficient after-data → `409` and the saving stays potential — simulated numbers are never called realized; a caller-measured `actual_cost_after` is accepted and labelled `source="reported"`.
- **Audit trail:** append-only `audit_logs` table (actor, action, from→to, details, request id) written on every transition; `GET /api/recommendations/audit-logs` (newest first, bounded).
- `GET /api/recommendations/savings` — potential (OPEN+APPROVED), approved, implemented, verified, **realized** (VERIFIED-only measured sum) and rejected-foregone, per status.
- `/savings` UI: five stage cards + lifecycle breakdown + verification explanation; detail page gained Mark-implemented / Verify buttons.
- Tests: 8 new (190 total) — approve/reject/implement/verify flows, dataset-recomputed realized savings, honesty guards (409 without after-data, negative stored), audit trail. Docs: [`docs/savings.md`](savings.md).

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
