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
| 13 | Savings Tracking | Potential vs realized savings with verification | ⬜ Pending |
| 11 | GCP Integration | Billing Export → BigQuery (cost-protected), real providers | ⬜ Pending |
| 14 | Monitoring / Freshness | Metrics, structured logs, SLOs, STALE/FRESH labelling | ⬜ Pending |
| 15 | Terraform | IaC for GCP resources with plan-review + destroy documentation | ⬜ Pending |
| 16 | Security | Least-privilege IAM, Secret Manager, Gitleaks/Trivy | ⬜ Pending |
| 17 | CI/CD | GitHub Actions: lint → test → build → security scan → Docker | ⬜ Pending |
| 18 | FinOps Health Score | Heuristic score: visibility, allocation, optimization, governance, forecasting, automation | ⬜ Pending |
| 19 | Reports | Daily/weekly/monthly report generation | ⬜ Pending |
| 20 | AI Advisor | Read-only AI Cloud Cost Advisor with structured context + audit log | ⬜ Pending |
| 21 | Demo Scenarios | Scripted incidents/scenarios (idle VM, spike, budget risk, …) | ⬜ Pending |
| 22 | Portfolio Preparation | README polish, screenshots, demo video, CV & interview docs | ⬜ Pending |

Milestone grouping:

- **Foundation:** 0–1 · **Core product:** 2–12 · **Cloud & hardening:** 13–17 · **FinOps depth & portfolio:** 18–21

## 2. Current phase: PHASE 12 — Observability & SRE (complete)

- **Metrics (§40, all exposed on `/metrics`):** `http_requests_total`, `http_request_duration_seconds` (request middleware, route-templated labels), `billing_records_processed_total` (ingestion), `billing_data_freshness_seconds` (gauge, set on ingest), `recommendations_generated_total` + `recommendation_runs_total{result}` (engine), `forecast_runs_total{result}` (forecast), `bigquery_query_duration_seconds` (billing provider).
- **Structured JSON logs** — one JSON line per request with request id, method, path, status, duration; correlation via request-id context var.
- **SLIs/SLOs (§43):** `GET /api/reliability` compares availability (≥ 99.5%), billing freshness (< 24h) and recommendation success (≥ 99%) against targets with met/not-met — the demo dataset honestly fails the freshness SLO.
- **Alerting:** `GET /api/alerts` evaluates in-process alerts (BillingDataStale/Missing, APIAvailabilityLow, RecommendationPipelineFailing) linked to runbooks; `monitoring/prometheus-rules.yml` mirrors them as Prometheus rules for real deployments.
- **Incidents + runbooks:** `docs/incidents/INC-001..005` (billing stale, BigQuery failure, API outage, recommendation failure, forecast failure) with exercised MTTD/MTTR; `docs/runbook.md` triage + per-alert procedures.
- Tests: 11 new (174 total) covering metric exposition, counter increments, SLI/SLO contract, stale-alert firing. README status/roadmap refreshed (README content restored after a Phase 10 script overwrite).

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
