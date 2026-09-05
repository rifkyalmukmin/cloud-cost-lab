# Project Roadmap — Cloud Cost Lab

> Status: living document · Last updated: 2026-09-05
> Rule: one phase at a time. A phase is never "done" because it compiles — see Definition of Done below.

---

## 1. Phase overview

| # | Phase | Scope | Status |
| --- | --- | --- | --- |
| 0 | Planning & Foundation | Architecture, ADRs, repository structure, cost-safety & security strategy, roadmap | ✅ **Done (this commit)** |
| 1 | Local Mock Platform | FastAPI + PostgreSQL + Docker Compose + mock dataset, provider abstraction, `/health` | ⬜ Pending |
| 2 | Cost Explorer | Cost aggregation, WoW/MoM, breakdowns, filters, first dashboard pages | ⬜ Pending |
| 3 | Resource Inventory | Resources, usage series, cost↔utilization linkage | ⬜ Pending |
| 4 | Recommendation Engine | Idle detection, rightsizing, storage rules, lifecycle (OPEN→…→VERIFIED) | ⬜ Pending |
| 5 | Budget | Budget model, thresholds, projected month-end, budget-risk alerts | ⬜ Pending |
| 6 | Forecasting | 30-day moving average / linear regression with range | ⬜ Pending |
| 7 | Anomaly Detection | Rolling average + threshold; z-score later | ⬜ Pending |
| 8 | Savings Tracking | Potential vs realized savings with verification | ⬜ Pending |
| 9 | GCP Integration | Billing Export → BigQuery (cost-protected), real providers | ⬜ Pending |
| 10 | Monitoring / Freshness | Metrics, structured logs, SLOs, STALE/FRESH labelling | ⬜ Pending |
| 11 | Terraform | IaC for GCP resources with plan-review + destroy documentation | ⬜ Pending |
| 12 | Security | Least-privilege IAM, Secret Manager, Gitleaks/Trivy | ⬜ Pending |
| 13 | CI/CD | GitHub Actions: lint → test → build → security scan → Docker | ⬜ Pending |
| 14 | FinOps Health Score | Heuristic score: visibility, allocation, optimization, governance, forecasting, automation | ⬜ Pending |
| 15 | Reports | Daily/weekly/monthly report generation | ⬜ Pending |
| 16 | AI Advisor | Read-only AI Cloud Cost Advisor with structured context + audit log | ⬜ Pending |
| 17 | Demo Scenarios | Scripted incidents/scenarios (idle VM, spike, budget risk, …) | ⬜ Pending |
| 18 | Portfolio Preparation | README polish, screenshots, demo video, CV & interview docs | ⬜ Pending |

Milestone grouping:

- **Foundation:** 0–1 · **Core product:** 2–8 · **Cloud & hardening:** 9–13 · **FinOps depth & portfolio:** 14–18

## 2. Current phase: PHASE 0 (complete)

Delivered in this phase:

- Finalized architecture and technology decisions ([`docs/architecture.md`](architecture.md), ADR-001…ADR-005).
- Repository skeleton (`apps/`, `analytics/`, `data/mock/`, `terraform/`, `monitoring/`, `scripts/`, `docs/`, `.github/workflows/`) with per-directory scope notes.
- Cost-safety and security strategy ([`docs/cost-safety.md`](cost-safety.md)).
- `.gitignore` (secrets/credentials/env excluded) and `.env.example` (`DEMO_MODE=true` default).
- No business implementation — deliberately.

## 3. Next phase: PHASE 1 — Local Mock Platform (not started)

Planned scope: docker-compose (api + web placeholder + postgres), FastAPI skeleton with `/health` + `/ready`, PostgreSQL schema/migrations, mock dataset in `data/mock/`, `MockBillingProvider`/`MockUsageProvider` behind the provider interfaces, pytest for provider loading. Entry criteria: this phase merged. **Do not start until explicitly instructed.**

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
