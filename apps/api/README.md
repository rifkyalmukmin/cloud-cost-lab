# apps/api — Backend API

FastAPI + Python backend for Cloud Cost Lab.

**Status: not implemented yet (Phase 1).** This directory currently holds only the plan below — no application code.

## Planned responsibilities

- HTTP API (`/health`, `/ready`, `/api/cost/*`, `/api/resources/*`, `/api/recommendations/*`, `/api/savings`, `/api/forecast`, `/api/budget`, `/api/anomalies`, `/api/finops-score`).
- Data provider abstraction:

  ```text
  BillingDataProvider
  ├── MockBillingProvider   (data/mock/*.json, DEMO_MODE=true)   ← default
  └── RealBillingProvider   (GCP Billing Export → BigQuery)      ← Phase 9
  ```

- PostgreSQL access layer (SQLAlchemy/Alembic to be decided in Phase 1).
- Recommendation engine orchestration (Phase 4) with the lifecycle
  `OPEN → APPROVED → REJECTED → IMPLEMENTED → VERIFIED`.
- Structured JSON logging, request IDs, bounded queries, pagination.

## Ground rules

- No credentials in code — configuration via environment variables (see `/.env.example`).
- Every query is bounded; no unbounded datasets over the API.
- Demo mode must work with zero GCP access.
