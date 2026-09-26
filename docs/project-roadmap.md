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

## 2. Current phase: PHASE 9 — GCP Monitoring Integration (complete, dormant)

> Safety: code + tests only — no GCP resource created; activation is the documented manual step in [`docs/gcp-setup.md`](gcp-setup.md).

- `MonitoringDataProvider` interface with `MockMonitoringProvider` (demo dataset unchanged) and `GCPMonitoringProvider` (Cloud Monitoring via injected runner; ADC/WIF, optional `gcp` extra; real mode without monitoring config falls back to `EmptyMonitoringProvider`).
- Metrics collected: CPU (0-1 → %), memory/disk (Ops Agent), network in/out (bytes → MB), **connections** (new `resource_usage.connections` column, migration 0004) and request counts; missing series ⇒ null (never 0), zero metrics kept, **stale series (newest sample > `GCP_MONITORING_MAX_AGE_DAYS`) dropped** instead of ingested as current; bounded 30-day window; metric failure aborts the load (`GCPMonitoringError`).
- Recommendations strengthened with performance evidence: `IdleComputeRule` now corroborates with request counts (avg > 10/day ⇒ never idle) and open connections (avg > 2 ⇒ never idle), each added as evidence lines — cost alone ($30/month, no monitoring) produces nothing (unit-tested).
- Tests: 15 new (163 total). Docs: [`docs/gcp-monitoring.md`](gcp-monitoring.md), [`docs/utilization-analysis.md`](utilization-analysis.md) (renamed from resource-analysis.md).

## 3. Next phase: not started

Candidates per the user's sequencing: savings tracking, Terraform, or security hardening. **Do not start until explicitly instructed.**

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
