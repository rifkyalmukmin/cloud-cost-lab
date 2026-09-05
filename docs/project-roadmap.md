# Project Roadmap — Cloud Cost Lab

> Status: living document · Last updated: 2026-09-05
> Rule: one phase at a time. A phase is never "done" because it compiles — see Definition of Done below.

---

## 1. Phase overview

| # | Phase | Scope | Status |
| --- | --- | --- | --- |
| 0 | Planning & Foundation | Architecture, ADRs, repository structure, cost-safety & security strategy, roadmap | ✅ **Done (this commit)** |
| 1 | Local Mock Platform | FastAPI + PostgreSQL + Docker Compose + mock dataset, provider abstraction, `/health` | ✅ **Done** |
| 2 | Cost Explorer | Cost aggregation, WoW/MoM, breakdowns, filters, first dashboard pages | ✅ **Done** |
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

## 2. Current phase: PHASE 2 — Cost Dashboard (complete)

Delivered in this phase:

- Next.js 15 + TypeScript (strict) + Tailwind v4 + shadcn/ui + Recharts dashboard in `apps/web`.
- `/` Overview: Current Month (MTD), Previous Month, MoM Change (**MTD vs prior MTD**, not partial-vs-full), Projected Month-End (**linear run-rate, labelled estimate**), Potential Savings (**honest empty state** until Phase 4), daily cost trend, and cost by service / project / environment — every number fetched from the Phase 1 API.
- `/cost` Cost Explorer: date/service/project/environment filters (option lists fetched from the API), daily/weekly/monthly trend switch, three breakdown tables, and server-side paginated cost records (10/25/50 per page).
- Uniform section states everywhere: loading (skeleton), error (API message + request id + retry), empty (hint), success; refetches dim instead of flashing.
- Typed API client (`lib/api.ts`) mirroring the FastAPI schemas; `useApi` hook (abortable + retryable); derived metrics as pure unit-tested functions (vitest, 8 tests).
- Backend: CORS for the dashboard origin (`CORS_ORIGINS`, GET-only, no credentials) + 2 new pytest tests (41 total).
- Verified in-browser: live data matches the API to the cent; filter → Cloud SQL = 194 records; pagination Page 2 of 8; reset works; zero console errors; mobile stacks cleanly.
- Docs: [`docs/dashboard.md`](dashboard.md) (pages, states, trade-offs), README + `apps/web/README.md` updated.

## 3. Next phase: PHASE 3 — Resource Inventory (not started)

Planned scope: `/api/resources` + `/api/resources/{id}` endpoints, resource inventory page with utilization↔cost linkage, resource detail view. Entry criteria: this phase merged. **Do not start until explicitly instructed.**

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
