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
| 5 | Recommendation Engine | Idle detection, rightsizing, storage rules, lifecycle (OPEN→…→VERIFIED) | ⬜ Pending |
| 6 | Budget | Budget model, thresholds, projected month-end, budget-risk alerts | ⬜ Pending |
| 7 | Forecasting | 30-day moving average / linear regression with range | ⬜ Pending |
| 8 | Anomaly Detection | Rolling average + threshold; z-score later | ⬜ Pending |
| 9 | Savings Tracking | Potential vs realized savings with verification | ⬜ Pending |
| 10 | GCP Integration | Billing Export → BigQuery (cost-protected), real providers | ⬜ Pending |
| 11 | Monitoring / Freshness | Metrics, structured logs, SLOs, STALE/FRESH labelling | ⬜ Pending |
| 12 | Terraform | IaC for GCP resources with plan-review + destroy documentation | ⬜ Pending |
| 13 | Security | Least-privilege IAM, Secret Manager, Gitleaks/Trivy | ⬜ Pending |
| 14 | CI/CD | GitHub Actions: lint → test → build → security scan → Docker | ⬜ Pending |
| 15 | FinOps Health Score | Heuristic score: visibility, allocation, optimization, governance, forecasting, automation | ⬜ Pending |
| 16 | Reports | Daily/weekly/monthly report generation | ⬜ Pending |
| 17 | AI Advisor | Read-only AI Cloud Cost Advisor with structured context + audit log | ⬜ Pending |
| 18 | Demo Scenarios | Scripted incidents/scenarios (idle VM, spike, budget risk, …) | ⬜ Pending |
| 19 | Portfolio Preparation | README polish, screenshots, demo video, CV & interview docs | ⬜ Pending |

Milestone grouping:

- **Foundation:** 0–1 · **Core product:** 2–9 · **Cloud & hardening:** 10–14 · **FinOps depth & portfolio:** 15–19

## 2. Current phase: PHASE 4 — Utilization Analysis (complete)

> Scope note: per the user's phase sequencing, PHASE 4 delivers the utilization **evidence layer**; the recommendation engine moves to PHASE 5 and consumes this evidence.

- `GET /api/utilization` — per-resource metric stats (avg / min / max / P95 / stddev / sample_count for CPU, memory, disk, network in/out, requests, latency, error rate) aggregated in SQL over a data-anchored window, with cost summed over the **same window**; filters (project/service/environment/date range) + pagination; `signal_counts` cover the full filtered set.
- `GET /api/utilization/{id}` — one resource: stats + daily series in the window; structured 404 for unknown ids.
- **Hard data rules:** a 0% sample is a real zero (kept in stats); a metric with no samples is listed in `missing_metrics`, never rendered as 0; per-row nulls are excluded from aggregates.
- **Evidence signals (heuristics, not recommendations):** low (avg CPU < 20%), high (> 80%), unstable (stddev > 15 pts with ≥ 7 samples), missing CPU — null when CPU has no samples.
- `/utilization` page — evidence summary cards, **Cost vs Utilization** bubble chart (cost-in-window vs avg CPU with 20%/80% reference lines), per-resource stats table with evidence badges, standard four-state sections.
- Backend: 19 new pytest tests (81 total) covering aggregation, P95 definition, nulls, zeros, missing metrics, time ranges, signals, cost linkage, pagination, 404/422. Docs: [`docs/resource-analysis.md`](resource-analysis.md).

## 3. Next phase: PHASE 5 — Recommendation Engine (not started)

Planned scope: idle detection, rightsizing, storage rules consuming the Phase 4 evidence; recommendation lifecycle (OPEN → APPROVED → IMPLEMENTED → VERIFIED) with human approval. Entry criteria: this phase merged. **Do not start until explicitly instructed.**

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
