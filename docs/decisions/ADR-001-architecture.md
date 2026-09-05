# ADR-001 — Modular Monolith Architecture

> Status: Accepted · Date: 2026-09-05 · Phase: 0

## Context

Cloud Cost Lab is a solo student project built on an 8 GB M1 MacBook, with three goals that pull in different directions:

1. It must **demonstrate real engineering architecture** (portfolio value) — not a CRUD toy.
2. It must **run locally and cheaply** — no cloud spend during development, no heavy local orchestration.
3. It must stay **understandable** — a 4th-semester student must be able to explain every part of it in an interview.

The system naturally splits into: data ingestion (mock/real providers), a cost database, analytics, a recommendation engine, and a dashboard. The question is how to package those parts.

## Decision

A **modular monolith in a single repository (monorepo)**:

- One FastAPI application (`apps/api`) owns HTTP APIs, data providers, and persistence.
- Analytics and recommendation logic live as plain Python packages (`analytics/`) imported by the API — not as separate services.
- One Next.js application (`apps/web`) consumes the API.
- Strict module boundaries (provider → storage → analytics → API) enforced by package layout and tests, so pieces can be extracted later if ever needed.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Microservices (separate collector, analytics, API services) | Operationally heavy (service discovery, inter-service auth, multiple deployments) for a solo project; adds failure modes without adding learning value at this scale. |
| Serverless-first (Cloud Run + Cloud Functions) | Puts cloud cost and deployment complexity in the development loop; contradicts "works offline in demo mode" and the 8 GB laptop constraint. |
| Single Django monolith | Viable, but FastAPI + Pydantic gives lighter data-validation ergonomics for an analytics-heavy workload (ADR-002). |
| Notebooks-only analysis | Fast to start but not a product: no API, no lifecycle, no testable business logic, weak portfolio signal. |

## Trade-offs

- Some indirection exists "early" (the provider abstraction, package boundaries). This is justified because switching mock/real data sources is a **current, explicit requirement** — not speculative generality.
- A monolith cannot scale components independently. Accepted: this project measures cost visibility, not throughput.
- Monorepo couples release cycles of API and UI. Accepted: solo developer, atomic commits, simpler CI.

## Consequences

- Positive: one `docker compose up` runs everything; tests are fast; the whole story fits in one repository and one demo; interviewers can trace every layer.
- Negative: discipline is required to keep modules decoupled; the "scale to 100 projects" answer is honest — it would require extraction, documented as future work.
- Revisit trigger: if analytics compute needs to run on a schedule independent of the API (a worker), extract it behind the same package interface.
