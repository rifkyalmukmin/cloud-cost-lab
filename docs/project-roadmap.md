# Project Roadmap — Cloud Cost Lab

> Status: living document · Last updated: 2026-09-12
> Rule: one phase at a time. A phase is never "done" because it compiles — see Definition of Done below.

---

## 1. Phase overview

| # | Phase | Scope | Status |
| --- | --- | --- | --- |
| 0 | Planning & Foundation | Architecture, ADRs, repository structure, cost-safety & security strategy, roadmap | ✅ **Done (this commit)** |
| 1 | Local Mock Platform | FastAPI + PostgreSQL + Docker Compose + mock dataset, provider abstraction, `/health` | ✅ **Done** |
| 2 | Cost Explorer | Cost aggregation, WoW/MoM, breakdowns, filters, first dashboard pages | ✅ **Done** |
| 3 | Resource Inventory | Resources, usage series, cost↔utilization linkage | ✅ **Done** |
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

## 2. Current phase: PHASE 3 — Resource Inventory (complete)

- `GET /api/resources` — filtered (`project_id`, `service`, `region`, `environment`, `status`, `owner`, `team` + `unallocated` audit flag) and paginated inventory; each item joins resource metadata with **monthly cost** (trailing 30 days anchored to the data, never the wall clock) and the **latest utilization** sample; response carries a `window` and a `summary` covering the full filtered set, ordered by monthly cost DESC.
- `GET /api/resources/{id}` — full detail: metadata, ownership, labels, all-time totals, daily **cost history** and **utilization** series; structured 404 with request id for unknown ids.
- `/resources` — inventory table (Resource, Type, Project, Region, Environment, Status, Monthly Cost, CPU, Memory, Potential Saving) with filter bar, UNALLOCATED-only checkbox, server-side pagination; rows link to the detail view.
- `/resources/{id}` — detail view with cost summary cards, cost-history chart, CPU/memory utilization chart, ownership, metadata and label cards.
- **UNALLOCATED rule** (CLAUDE.md §12): missing owner/team is surfaced as `null` + amber badge and a dedicated `unallocated=true` filter — ownership is never guessed. `potential_saving` stays explicitly `null` until Phase 4.
- Backend: 21 new pytest tests (62 total) covering filtering, pagination, 404/422, empty results, unallocated resources, and dataset cross-checks. Docs: [`docs/resource-inventory.md`](resource-inventory.md).
- Phase 2 (Cost Explorer) summary: see [`docs/dashboard.md`](dashboard.md).

## 3. Next phase: PHASE 4 — Recommendation Engine (not started)

Planned scope: idle detection, rightsizing, storage rules; recommendation lifecycle (OPEN → APPROVED → IMPLEMENTED → VERIFIED) with evidence, risk, confidence and human approval. Entry criteria: this phase merged. **Do not start until explicitly instructed.**

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
