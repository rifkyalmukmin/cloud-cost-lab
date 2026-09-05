# ADR-002 — Technology Stack

> Status: Accepted · Date: 2026-09-05 · Phase: 0

## Context

The stack must fit: a solo student, an 8 GB M1 MacBook, GCP as target cloud, analytics-heavy workloads (aggregations, forecasting heuristics), a dashboard UI, and employability as the real end goal. Each choice follows the project rule: state **What / Why / Alternative / Trade-off / Failure mode / Security / Cost** before adopting a technology.

## Decision

| Layer | Choice | Why | Alternatives considered | Key trade-off |
| --- | --- | --- | --- | --- |
| Frontend | **Next.js + TypeScript (strict) + Tailwind + shadcn/ui** | Dashboard-first framework; typed API contracts; huge ecosystem; aligns with job market | Vue/Nuxt, SvelteKit, plain React SPA + Express | Two languages in the repo (TS + Python) — accepted; mirrors real industry stacks |
| Backend | **FastAPI + Python + Pydantic** | Fast development; first-class validation; async; natural fit for data/analytics code | Django (heavier, ORM-centric), Flask (too minimal, manual validation), Node/Express (splits analytics from server language) | Python's packaging/typing story is weaker than TS — mitigated with type hints + mypy/ruff |
| Database | **PostgreSQL** | Window functions and CTEs for cost aggregations; JSONB for labels; production-realistic SQL practice | SQLite (fine for demo but hides real SQL skills; weak concurrency story), MySQL (less expressive JSON/window features for this use), MongoDB (no SQL analytics; wrong fit for relational cost data) | Slightly heavier local footprint than SQLite — one container, acceptable |
| Analytics | **SQL + Python; Pandas only where it clearly helps** | SQL does set-based aggregation efficiently; Pandas reserved for operations where it genuinely adds value | Pandas-everywhere, Polars, Spark | Pandas is memory-hungry on 8 GB — bounded by aggregating in SQL first |
| Cloud | **GCP** | Author's cloud; Billing Export → BigQuery and Cloud Monitoring are first-class FinOps building blocks | AWS (Cost Explorer API is more gated; pricing model harder for a learner), Azure (author has no account) | Ties the project to one provider — accepted, multi-cloud is a future provider implementation |
| IaC | **Terraform** | Industry standard, declarative, plan/apply/destroy lifecycle teaches review discipline | Pulumi (code-first, but less common in target job listings), gcloud scripts (not reproducible), Ansible (config mgmt, not provisioning) | HCL is another language to learn — accepted, it is the point |
| CI/CD | **GitHub Actions** | Native to the repo host; free tier sufficient | GitLab CI, Jenkins | GitHub-hosted runners have limits — pipelines kept small |
| Security tooling | **Gitleaks + Trivy** | Secret scanning + dependency/image scanning with minimal setup | Bandit, Snyk | Scanners produce noise — findings triaged per phase |
| AI | **Pluggable LLM provider, read-only** | Avoids hard dependency on one vendor; AI stays an advisor (ADR-005) | Local LLM (impossible on 8 GB), no AI | External API adds token cost — bounded context, optional feature |

## Failure modes (per major choice)

- FastAPI: unbounded endpoints can dump huge datasets → every endpoint paginates and bounds queries.
- PostgreSQL: unbounded raw billing retention → bounded retention, aggregated tables.
- Terraform: `apply` mistakes create real cost → plan review gate + destroy documentation (`docs/cost-safety.md`).
- BigQuery: full scans cost money → partition filters, column pruning, dry-run estimates (ADR-004).

## Consequences

- Two-language repo requires both toolchains in CI (Phase 13).
- Every dependency must be pinned and justified; popular-but-unneeded tech (message queues, Kubernetes, Redis) is deliberately excluded until a phase proves the need.
- The stack reads like real junior-cloud-job requirements, which is the primary portfolio objective.
