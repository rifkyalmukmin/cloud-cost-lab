# Cloud Cost Lab — Project Overview

> GCP FinOps & Cloud Cost Optimization Platform · portfolio project by Rifky Al Mukmin

## The one-paragraph pitch

Cloud Cost Lab is a full-stack FinOps platform that connects cloud **cost** with resource **utilization** and **performance**. It aggregates billing and monitoring data through a provider abstraction (synthetic demo data by default, real GCP BigQuery/Monitoring providers code-complete), detects idle/oversized resources and cost anomalies with measured evidence, produces priority-ranked recommendations that require **human approval**, measures **realized savings** from actual before/after cost data, forecasts spend with explicit uncertainty ranges, and watches budgets — all observable through Prometheus metrics, SLIs/SLOs and an append-only audit trail.

## What it demonstrates

| Skill | Where |
| --- | --- |
| Backend engineering | FastAPI service, 20+ documented endpoints, Alembic migrations, layered architecture |
| Data/analytics | SQL aggregation (avg/min/max/P95/σ in-database), rolling baselines, linear regression + residual bounds |
| FinOps practice | Potential vs realized savings, budget SLOs, governance policies, UNALLOCATED cost handling |
| Frontend | Next.js 15 dashboard, 9 pages, typed API contracts, four-state data handling |
| Infrastructure as Code | Terraform modules (IAM, BigQuery, Storage, Compute) — plan-reviewed, never auto-applied |
| DevSecOps | GitHub Actions: ruff/mypy/pytest, ESLint/tsc/vitest/build, Gitleaks, Trivy, multi-arch non-root Docker to GHCR |
| SRE | 7 Prometheus metrics, SLIs vs SLOs, alerting, structured JSON logs, incident docs with MTTD/MTTR |
| Security | Least-privilege IAM design, no-secrets discipline, prompt-injection defence in the AI layer |
| Responsible AI | Read-only advisor with "insufficient evidence" honesty and injection refusal |

## Key engineering decisions

1. **Demo-first** — the entire platform runs on a deterministic synthetic dataset with zero cloud credentials; real GCP providers implement the same interface and stay dormant until a human enables them.
2. **Evidence over guesses** — every recommendation carries measured evidence (utilization windows, cost deltas, sample counts); rules refuse to fire when data is missing; missing metrics are `null`, never fabricated zeros.
3. **Human approval** — the engine only recommends. APPROVED → IMPLEMENTED → VERIFIED transitions are human decisions, recorded in an append-only audit log.
4. **Honest numbers** — forecasts carry ranges and confidence; stale data is labelled STALE; negative realized savings are stored as measured; simulated estimates are never called realized.
5. **Cost-safety for itself** — no billable GCP resource was created during development; Terraform is validated and plan-reviewed but not applied.

## Scale & quality

- **198 backend tests** (pytest, PostgreSQL test database, strict mypy: 0 issues) · **8 frontend tests** (vitest, strict tsc) · ruff + ESLint clean.
- 190+ documentation lines across 20 docs: architecture, cost model, per-phase docs, ADRs, incident reports, runbook, and a full portfolio pack.
- Deterministic demo dataset: 12 resources across 4 projects, 97 days of cost + utilization, designed-in scenarios (idle VM, oversized VMs, cost spikes, unallocated resource).

## What it is not

- Not a production SaaS: single-user demo deployment, single-host docker compose.
- Not connected to real GCP data by default — enabling it is a documented manual decision.
- Not an autonomous optimizer: it never modifies infrastructure; every action is human-driven.
