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

- **Foundation:** 0–1 · **Core product:** 2–11 · **Cloud & hardening:** 12–16 · **FinOps depth & portfolio:** 17–20

## 2. Current phase: PHASE 6 — Budget & Governance (complete)

> Scope note: per the user's phase sequencing, PHASE 6 = budget + governance policies (CLAUDE.md's later phases shifted by one).

- `budgets` table (migration 0003): name, scope (`all`/`project`/`service`/`environment` + value), monthly period, limit, warning/critical thresholds; **status derived at read time** from net month-to-date spend against the latest month in the data (never the wall clock). Demo seed: $50/month, 70/90.
- Inclusive status bands, unit-tested across 69/70/89/90/99/100/101 (exactly 70 → WARNING, 90 → CRITICAL, 100 → EXCEEDED) plus custom thresholds, fractional values and degenerate limits.
- `GET /api/budget` returns per-budget evaluation: spend (net MTD + gross + daily average), remaining, percentage, **linear run-rate projected month-end (labelled estimate)** and `forecast_over_budget` — the demo budget is HEALTHY at ~21% MTD yet forecasts ~$63.7 against the $50 limit (§15 budget-risk scenario).
- `POST /api/budget` creates budgets with strict server-side validation (positive limit, thresholds in (0,100), warning strictly below critical, scope value required, unknown fields forbidden) — 422 + nothing created on bad input. CORS now allows POST from configured origins only (no credentials).
- `policies` table + five advisory policies evaluated at read time (CLAUDE.md §32): REQUIRE_OWNER_LABEL (WARNING: legacy sandbox), REQUIRE_ENVIRONMENT_LABEL (PASS), MAX_MONTHLY_COST (VIOLATION: sql-shop-orders-prod $17.27 > $10; **strictly-above** boundary unit-tested at 10.00/10.01), NO_PUBLIC_DATABASE (WARNING "cannot verify" — never a false PASS without reachability data), DEV_RESOURCE_SCHEDULE (WARNING: three dev resources without schedule labels).
- Violations produce warnings/evidence/audit information only — no endpoint can modify cloud infrastructure. `/budget` and `/policies` pages render statuses, threshold markers, findings and the caveats.
- Backend: 12 new pytest tests (117 total) covering the threshold ladder, budget evaluation vs dataset recomputation, POST validation matrix, CORS POST preflight, and policy boundaries. Docs: [`docs/budget.md`](budget.md), [`docs/governance.md`](governance.md).

## 3. Next phase: PHASE 7 — Forecasting (not started)

Planned scope: 30-day forecast with moving average / linear regression and an explicit range (CLAUDE.md §27). Entry criteria: this phase merged. **Do not start until explicitly instructed.**

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
