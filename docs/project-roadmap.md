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

- **Foundation:** 0–1 · **Core product:** 2–10 · **Cloud & hardening:** 11–15 · **FinOps depth & portfolio:** 16–20

## 2. Current phase: PHASE 5 — Recommendation Engine (complete)

> Scope note: per the user's phase sequencing, PHASE 5 = recommendation engine (CLAUDE.md's later phases shifted by one).

- Pluggable `RecommendationRule` interface (`evaluate / explain / calculate_saving / calculate_risk / confidence`) with five rules: `IdleComputeRule` (CPU < 5% + burst P95 guard + minimal network + ≥ 7 days), `OversizedComputeRule` (CPU < 20% AND mem < 40% AND stable AND P95 headroom, one-step-down shape, ~50% saving estimate), `UnusedDiskRule` (detached state; silent on the disk-less mock dataset), `StorageRetentionRule` (near-zero-traffic buckets; snapshot branches await provider data), `CostAnomalyRule` (rolling 14-day baseline, 1.3× + $0.05/day floor, ≥ 3-day runs, ≥ $0.50 excess; savings = observed excess).
- `recommendations` table (migration 0002) with the OPEN/APPROVED/REJECTED/IMPLEMENTED/VERIFIED lifecycle; re-runs upsert by (rule_id, scope_key) and **preserve human decisions**; seeding runs the engine so the UI has findings.
- API: `GET /api/recommendations` (filters status/rule/risk/priority/resource/project, sort priority|savings|recent, pagination, summary incl. open potential savings), `GET /api/recommendations/{id}`, `POST /run` (recommendation mode only — never touches infrastructure), `POST /{id}/approve` + `/{id}/reject` (OPEN-only, else 409).
- `/recommendations` UI: summary cards, filter/sort bar, findings table, detail page answering WHY / EVIDENCE / SAVING / RISK / CONFIDENCE / EFFORT with raw metric values, and Approve/Reject buttons (decision only, no action).
- **No false positives (test-asserted):** the dataset yields exactly 5 findings (1 idle, 2 oversized, 2 anomalies); CPU = 5% / 20% exactly, spiky P95, unstable stddev, missing CPU/cost, tiny cost jitter all stay silent.
- Backend: 24 new pytest tests (105 total). Docs: [`docs/recommendation-engine.md`](recommendation-engine.md).

## 3. Next phase: PHASE 6 — Budget (not started)

Planned scope: budget model, thresholds, projected month-end, budget-risk alerts (CLAUDE.md §15). Entry criteria: this phase merged. **Do not start until explicitly instructed.**

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
