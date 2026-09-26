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
| 15 | Savings Tracking | Potential vs realized savings with verification | ⬜ Pending |
| 11 | GCP Integration | Billing Export → BigQuery (cost-protected), real providers | ⬜ Pending |
| 16 | Monitoring / Freshness | Metrics, structured logs, SLOs, STALE/FRESH labelling | ⬜ Pending |
| 17 | Terraform | IaC for GCP resources with plan-review + destroy documentation | ⬜ Pending |
| 18 | Security | Least-privilege IAM, Secret Manager, Gitleaks/Trivy | ⬜ Pending |
| 19 | CI/CD | GitHub Actions: lint → test → build → security scan → Docker | ⬜ Pending |
| 20 | FinOps Health Score | Heuristic score: visibility, allocation, optimization, governance, forecasting, automation | ⬜ Pending |
| 21 | Reports | Daily/weekly/monthly report generation | ⬜ Pending |
| 22 | AI Advisor | Read-only AI Cloud Cost Advisor with structured context + audit log | ⬜ Pending |
| 23 | Demo Scenarios | Scripted incidents/scenarios (idle VM, spike, budget risk, …) | ⬜ Pending |
| 24 | Portfolio Preparation | README polish, screenshots, demo video, CV & interview docs | ⬜ Pending |

Milestone grouping:

- **Foundation:** 0–1 · **Core product:** 2–12 · **Cloud & hardening:** 13–17 · **FinOps depth & portfolio:** 18–21

## 2. Current phase: PHASE 15 — Portfolio Preparation (complete)

- README restructured to the 13 portfolio sections (overview, problem, architecture, stack, demo, screenshots, cost optimization, FinOps workflow, security, SRE, AI advisor, limitations, future roadmap) — every claim cross-checked against the implementation.
- Portfolio pack: [`docs/portfolio/`](portfolio/) with project overview, 5-minute demo script (Dashboard → Cost → Resources/Utilization → Recommendations → Savings → Forecast/Budget → AI Advisor), CV bullets, LinkedIn post (with an anti-exaggeration self-check) and 13 interview Q&As.
- 8 live screenshots captured from the running stack (`docs/screenshots/`) with a refresh guide; Overview Potential-Savings card now shows the live estimate from the recommendation engine (was a stale placeholder).
- No core business logic changed — presentation and documentation only.

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
