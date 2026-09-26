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
| 6 | Recommendation Engine | Idle detection, rightsizing, storage rules, lifecycle (OPEN→…→VERIFIED) | ⬜ Pending |
| 7 | Budget | Budget model, thresholds, projected month-end, budget-risk alerts | ⬜ Pending |
| 8 | Forecasting | 30-day moving average / linear regression with range | ⬜ Pending |
| 9 | Anomaly Detection | Rolling average + threshold; z-score later | ⬜ Pending |
| 10 | Savings Tracking | Potential vs realized savings with verification | ⬜ Pending |
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

## 2. Current phase: PHASE 7 — Forecasting & Cost Anomaly (complete)

- `GET /api/forecast` — 30-day projection (7–90) combining a 14-day **moving average** and an OLS **linear trend** (50/50 blend, both components exposed); expected + lower/upper bounds from the fit residuals (~80% interval, lower floored at 0) + a confidence label (HIGH/MEDIUM/LOW from history length and relative residual sigma); zero baseline and < 14-day history return honest empty/insufficient states instead of numbers. Data-anchored calendar-continuous series; forecast dates start after the last data day.
- `GET /api/anomalies` — point-level **unexpected cost increases** per (project, service, resource): rolling 14-day baseline mean + **z-score**, one-sided, noise-floored (≥ $0.05 and ≥ +25% and z ≥ 2.0 default); warm-up period never flagged; zero-variance baselines surface step-changes with `z_score: null` (never fabricated); severity LOW/MEDIUM/HIGH and confidence from evidence quality. Filters (severity/min z/project/service/environment/resource) + pagination.
- Relationship to Phase 5: the recommendation `CostAnomalyRule` groups spike days into run-level findings for the approval workflow; `/api/anomalies` exposes the underlying per-day detections.
- `/forecast` — summary cards (expected/range/confidence/trend) and a chart joining observed daily cost to the dashed expected line with the shaded ~80% interval; `/anomalies` — severity filter, min-z selector, findings table with z-scores and links to resource detail.
- Backend: 17 new pytest tests (134 total) covering the six required scenarios (insufficient data, zero baseline, missing values, spike, normal trend, large spike) plus dataset/API behaviour. Docs: [`docs/forecasting.md`](forecasting.md), [`docs/anomaly-detection.md`](anomaly-detection.md).

## 3. Next phase: PHASE 8 — Savings Tracking (not started)

Planned scope: potential vs realized savings with post-change verification (CLAUDE.md §23). Entry criteria: this phase merged. **Do not start until explicitly instructed.**

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
