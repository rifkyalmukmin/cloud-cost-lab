# Cloud Cost Lab

> **GCP FinOps & Cloud Cost Optimization Platform**

Cloud Cost Lab aggregates cloud cost and resource utilization data, detects waste and optimization opportunities, estimates **potential** savings, monitors budgets, forecasts future cost with explicit uncertainty, and produces evidence-based recommendations that require **human approval** before any impactful action.

**Current status: PHASE 0 — Foundation & Architecture complete. Application code starts in Phase 1.**

---

## 1. Problem

Cloud bills are opaque for most engineers. Typical questions that are hard to answer with a cloud console alone:

- Where did the money actually go this month, and why did it change?
- Which resources are idle or overprovisioned, and what evidence proves it?
- How much could be saved — and how much **was actually saved** after an optimization?
- Will we exceed the budget before the month ends?
- Which optimization should be done first, and what is the risk?

Cloud Cost Lab is built to answer these questions with data, not guesses.

## 2. Target users

- **Primary:** the project author — a 4th-semester informatics student building deep, demonstrable skills for Cloud Engineer / DevOps / Infrastructure / SRE / Platform / FinOps careers.
- **Secondary:** anyone learning FinOps on GCP with a small budget; small teams who want a readable cost-optimization reference implementation.

## 3. Why FinOps

FinOps connects engineering decisions (instance types, schedules, retention, labeling) to financial outcomes. Building this project demonstrates: cost visibility, cost allocation, resource efficiency, forecasting, governance, and cost-aware automation — the difference between "deployed something" and "operated it responsibly".

## 4. Architecture (summary)

```text
GCP (Billing Export + Monitoring)          ← Phase 9+ / or mock data (default)
            │
      Data Collector  (apps/api)           ← provider abstraction: Mock | Real
            │
      PostgreSQL (cost database)
            │
   Cost Analytics ── Usage Analytics       ← analytics/
            │
   Recommendation Engine                   ← rule-based + optional AI layer (read-only)
            │
   Next.js Dashboard (apps/web)            ← costs / savings / forecast / budget
            │
   Alerts → Human Approval → Optional bounded action
```

Full detail: [`docs/architecture.md`](docs/architecture.md).

## 5. Technology stack

| Layer | Choice | Rationale |
| --- | --- | --- |
| Frontend | Next.js + TypeScript (strict) + Tailwind + shadcn/ui | Dashboard-first, typed data contracts |
| Backend | FastAPI + Python + Pydantic | Fast to build, validation built-in, great for data work |
| Database | PostgreSQL | Window functions, JSONB for labels, production-realistic |
| Analytics | SQL + Python (Pandas only where it clearly helps) | Simple, testable business logic |
| Cloud | GCP | Author's cloud; Billing Export + Monitoring are first-class |
| IaC | Terraform | Reproducible, reviewable, destroyable infrastructure |
| CI/CD | GitHub Actions | Lint, test, build, security scans (Trivy, Gitleaks) |
| AI | Pluggable LLM provider, **read-only by default** | Analysis/explanation only; no destructive actions |

Trade-offs and rejected alternatives are documented in the [ADRs](docs/decisions/).

## 6. Demo mode (works without GCP)

The platform **must run with zero GCP credentials**:

```text
DEMO_MODE=true   →   synthetic billing + utilization data (data/mock/)
```

Mock and real data sources implement the same `BillingDataProvider` interface, so the dashboard and recommendation engine behave identically in both modes. See `docs/decisions/ADR-003-demo-mode.md`.

## 7. Cost safety

**This project must not become an expensive cloud project.** Core rules:

- Mock mode is the default; real GCP integration is opt-in (Phase 9+).
- No GCP resource is created without stating: purpose, cost, smallest configuration, shutdown and destroy path.
- `terraform apply` only after a reviewed plan; BigQuery queries are partition-filtered and column-pruned; budget alerts are configured early.
- Potential savings are labelled *potential*; savings are called *realized* only after verified post-change data.

Full policy: [`docs/cost-safety.md`](docs/cost-safety.md).

## 8. Security

- Least-privilege, read-only-by-default GCP service accounts (`cost-data-reader`, `monitoring-reader`; a separate `cost-optimizer` only for explicitly bounded actions).
- No service account keys, credentials, or `.env` files in git — Gitleaks + Trivy in CI (Phase 12–13), Secret Manager / Workload Identity Federation where feasible.
- AI is read-only and cannot delete resources, modify IAM, or touch Terraform state.

## 9. Repository structure

```text
cloud-cost-lab/
├── apps/
│   ├── api/            FastAPI backend (Phase 1)
│   └── web/            Next.js dashboard (Phase 2)
├── analytics/          cost / utilization / recommendations / forecasting modules
├── data/
│   └── mock/           synthetic demo dataset (Phase 1)
├── terraform/          modules + environments (Phase 11)
├── monitoring/         SLOs, metrics, alert rules (Phase 10)
├── scripts/            operational helpers
├── docs/
│   ├── architecture.md
│   ├── project-roadmap.md
│   ├── cost-safety.md
│   └── decisions/      ADR-001 … ADR-005
├── .github/workflows/  CI/CD (Phase 13)
├── .env.example
├── .gitignore
├── CLAUDE.md           project rules
└── README.md
```

## 10. Roadmap

18 phases, one step at a time — from local mock platform (Phase 1) through GCP integration, forecasting, FinOps score, AI advisor, and portfolio preparation (Phase 18). Current phase status: [`docs/project-roadmap.md`](docs/project-roadmap.md).

## 11. Limitations (honest)

- Phase 0 contains documentation and structure only — there is no application code yet.
- Single-cloud (GCP) by design for now; multi-cloud is a future extension via the provider abstraction.
- Forecasting starts with simple methods (moving average, linear regression) and always shows a range, not exact numbers.
- Recommendations are heuristics with evidence and confidence levels — not guarantees.

## 12. Future work

Realized-savings verification loop, unit economics (cost per request/user), what-if cost simulator, policy engine expansion, multi-cloud providers, and richer AI-assisted root-cause analysis — each introduced only in its planned phase.
