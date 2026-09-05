# Architecture — Cloud Cost Lab

> Status: Accepted (Phase 0) · Date: 2026-09-05
> Related decisions: [ADR-001](decisions/ADR-001-architecture.md) (architecture shape) · [ADR-002](decisions/ADR-002-technology-stack.md) (stack) · [ADR-003](decisions/ADR-003-demo-mode.md) (demo mode) · [ADR-004](decisions/ADR-004-gcp-integration.md) (GCP) · [ADR-005](decisions/ADR-005-ai-safety.md) (AI safety)

---

## 1. Problem this architecture solves

Cloud cost data is scattered: billing lives in Billing Export/BigQuery, utilization lives in Cloud Monitoring, and neither answers "what should I do and why?". The architecture joins **cost data + utilization data → evidence → recommendations → approval → verified savings**, while keeping the whole system small enough to run on an 8 GB laptop and cheap enough to demo without fear.

## 2. Architectural goals

GCP-first · small and understandable · modular · extensible toward multi-cloud · safe by default · data-driven · cost-aware · observable · testable.

Non-goals for now: horizontal scalability, multi-tenancy, Kubernetes, microservices, real-time streaming.

## 3. High-level view

```text
                ┌───────────────────────────────────────────────┐
                │                    GCP                        │
                │   Billing Export (BigQuery)   Cloud Monitoring│
                └───────────────┬───────────────┬───────────────┘
                                │               │
                                ▼               ▼
                        ┌───────────────────────────┐
                        │      Data Collector       │   apps/api
                        │  BillingDataProvider:     │   (provider abstraction,
                        │   ├ MockBillingProvider   │    DEMO_MODE=true → Mock)
                        │   └ RealBillingProvider   │
                        │  UsageDataProvider:       │
                        │   ├ MockUsageProvider     │
                        │   └ RealUsageProvider     │
                        └────────────┬──────────────┘
                                     ▼
                        ┌───────────────────────────┐
                        │  PostgreSQL (cost DB)     │   cost_records, resources,
                        │                           │   resource_usage, budgets,
                        │                           │   recommendations, …
                        └────────────┬──────────────┘
                                     ▼
              ┌──────────────────────┴─────────────────────┐
              ▼                                            ▼
   ┌─────────────────────┐                     ┌─────────────────────┐
   │   Cost Analytics    │                     │  Usage Analytics    │   analytics/
   │ (aggregation, WoW/  │                     │ (utilization, cost- │
   │  MoM, top-N,        │                     │  to-resource join)  │
   │  unallocated)       │                     └──────────┬──────────┘
   └──────────┬──────────┘                                │
              └──────────────────┬────────────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │ Recommendation Engine │   analytics/recommendations
                     │  ├ Rule-based rules   │   (pluggable: evaluate / explain /
                     │  └ AI layer (Phase 16,│    calculate_saving / calculate_risk /
                     │    READ-ONLY)         │    confidence)
                     └───────────┬───────────┘
                                 ▼
                     ┌───────────────────────┐
                     │  Cost Dashboard (UI)  │   apps/web — Next.js
                     │  Costs · Savings ·    │
                     │  Forecast · Budget ·  │
                     │  Utilization · AI     │
                     └───────────┬───────────┘
                                 ▼
                Alerts → Human Approval → Optional bounded action
                         (lifecycle: OPEN → APPROVED → IMPLEMENTED → VERIFIED;
                          audit-logged; never auto-destructive)
```

## 4. Components and responsibilities

| Component | Location | Responsibility | Phase |
| --- | --- | --- | --- |
| Data Collector / Providers | `apps/api` | Fetch or synthesize billing + usage data; normalize to the core data model | 1 (mock), 9 (real) |
| Cost Database | PostgreSQL | Durable storage for costs, resources, usage, budgets, recommendations, audit logs | 1 |
| Cost Analytics | `analytics/cost` | Aggregation by project/service/SKU/region/environment/date; WoW/MoM; top-N; unallocated cost | 2 |
| Usage Analytics | `analytics/utilization` | CPU/memory/disk/network analysis; joins utilization to cost | 3 |
| Recommendation Engine | `analytics/recommendations` | Pluggable rules producing evidence-based recommendations with savings, risk, confidence, effort | 4+ |
| Budget & Alerts | `apps/api` + UI | Budget thresholds (70/90/100%), projected month-end, forecast-over-budget risk | 5 |
| Forecasting | `analytics/forecasting` | 30-day moving average / linear regression with a range | 6 |
| Anomaly Detection | `analytics` | Rolling average + threshold (phase 1 of detection), z-score later | 7 |
| Savings Tracking | `apps/api` + DB | Potential vs **realized** savings (realized only after verified post-change data) | 8 |
| GCP Integration | `apps/api` + `terraform/` | Billing Export → BigQuery (cost-protected queries), Cloud Monitoring metrics | 9 |
| Observability | `monitoring/` | Metrics, structured logs, SLOs (freshness < 24h, availability ≥ 99.5%) | 10 |
| Terraform | `terraform/` | Reproducible, reviewable, destroyable GCP infrastructure | 11 |
| Security hardening | repo-wide | Least-privilege IAM, secret scanning, dependency scanning | 12–13 |
| FinOps Health Score | `analytics` | Heuristic score over visibility/allocation/optimization/governance/forecasting/automation | 14 |
| Reports | `apps/api` + `docs/reports` | Daily/weekly/monthly Markdown/HTML reports | 15 |
| AI Cloud Cost Advisor | `apps/api` | Read-only Q&A over structured context; same approval lifecycle as rules | 16 |

## 5. Data provider abstraction (core design decision)

```text
BillingDataProvider (interface)
├── MockBillingProvider   reads data/mock/*.json      ← default (DEMO_MODE=true)
└── RealBillingProvider   GCP Billing Export → BigQuery (cost-protected queries)

UsageDataProvider (interface)
├── MockUsageProvider     synthetic utilization time series
└── RealUsageProvider     Cloud Monitoring metrics
```

Consequences:

- The UI/API/analytics layers never know which provider is active — demo and real modes are interchangeable.
- Deterministic mock data makes demos and tests reproducible.
- Real integration can be added later without touching the dashboard or analytics code.
- Trade-off: the mock schema must be kept aligned with the real Billing Export schema; validated when Phase 9 lands.

## 6. Core data model (summary)

- **CostRecord** — project, service, SKU, region, resource, usage date/amount/unit, cost, currency, credits, net cost, environment, labels. The grain for all cost analytics.
- **ResourceRecord** — resource identity, type, project, region/zone, status, lifecycle timestamps, labels/environment.
- **UsageRecord** — per-resource metric samples (CPU, memory, disk, network, requests, latency, errors). Not every resource exposes every metric — the model stays flexible (nullable metrics).

PostgreSQL tables (minimum set): `projects, services, resources, resource_usage, cost_records, budgets, recommendations, savings, anomalies, forecast_runs, policies, audit_logs`, indexed on `project_id, service, usage_date, resource_id, environment`. Raw data retention is bounded — no unlimited accumulation.

Cost dimensions supported everywhere: Project · Service · SKU · Region · Resource · Environment · Team · Application · Label · Date. Missing attribution is reported as **UNALLOCATED** — never guessed.

## 7. Recommendation architecture

Rules are pluggable and independent: `IdleComputeRule, OversizedComputeRule, UnusedDiskRule, StorageRetentionRule, ArtifactRetentionRule, CloudSQLRightsizingRule, GKEOptimizationRule, BudgetRiskRule, CostAnomalyRule`. Each exposes `evaluate() / explain() / calculate_saving() / calculate_risk() / confidence()`.

Every recommendation must answer: **what is wrong · what evidence supports it · how much could be saved (potential) · what is the risk · what effort is required · who approves · what happens next.**

Lifecycle: `Detect → Recommend → Approve → Implement → Measure → Verify` with states `OPEN → APPROVED → REJECTED → IMPLEMENTED → VERIFIED`. Savings are **realized** only after post-change data confirms them. The AI layer (Phase 16) feeds the same lifecycle and is read-only (ADR-005).

## 8. Deployment topology

- **Local (default):** `backend + frontend + postgres` via Docker Compose, mock mode, no GCP credentials, sized for an 8 GB M1 MacBook.
- **GCP (later, opt-in):** smallest-practical resources only; anything billable is created via reviewed Terraform with a documented destroy path (see `docs/cost-safety.md`).

## 9. Security architecture (summary)

Least privilege with separated read-only identities (`cost-data-reader`, `monitoring-reader`) and a distinct `cost-optimizer` for explicitly bounded actions; no service account keys in git; secrets via environment/GitHub Secrets/Secret Manager; Workload Identity Federation for CI when feasible; Gitleaks + Trivy; AI read-only. Details: `docs/cost-safety.md`, ADR-004, ADR-005.

## 10. Observability (planned)

Structured JSON logs (timestamp/level/service/operation/duration_ms); metrics `http_requests_total`, `http_request_duration_seconds`, `cost_records_processed_total`, `recommendations_generated_total`, `forecast_runs_total`, `billing_query_duration_seconds`; SLOs on API availability, data freshness (<24h, else `STALE`), pipeline success. Data quality score tracks missing labels, missing resource IDs, duplicates, malformed and stale records.

## 11. Trade-offs and failure modes

| Decision | Trade-off accepted | Failure mode & mitigation |
| --- | --- | --- |
| Modular monolith (ADR-001) | No independent scaling of analytics vs API | Not needed at this scale; module boundaries allow later extraction |
| Mock-first data (ADR-003) | Mock schema can drift from real Billing Export | Schema contract validated in Phase 9; provider tests pin the contract |
| BigQuery for billing data (ADR-004) | Query costs if unbounded | Partition filters, column pruning, dry-run estimates, bounded retention |
| Rule-based recommendations | Heuristics can misfire on unusual workloads | Evidence + confidence + risk on every recommendation; human approval gate |
| AI layer (ADR-005) | LLM hallucination risk | Read-only, structured context, no destructive capability, audit log |

## 12. Future evolution

Multi-cloud providers behind the same data interfaces; extraction of analytics into a worker if compute grows; GKE/Cloud Run optimization modules when they add learning value; unit economics and what-if simulation as product depth. Each extension is a new ADR.
