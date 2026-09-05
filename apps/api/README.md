# apps/api — Backend API

FastAPI + Python backend for Cloud Cost Lab.

**Status: Phase 1 IMPLEMENTED — mock cost analytics engine.** Serves cost aggregations from PostgreSQL, loaded from the deterministic mock dataset (`DEMO_MODE=true`). No GCP access required.

## Layout

```text
apps/api/
├── src/costlab/
│   ├── config.py           settings from environment variables (.env supported)
│   ├── logging_config.py   structured JSON logs + request-id context var
│   ├── db/                 engine, session factory, SQLAlchemy models
│   ├── providers/          BillingDataProvider / UsageDataProvider + mock & real impls
│   ├── ingestion/          snapshot validation + loader (idempotent seeding)
│   ├── analytics/          cost aggregation queries (SQL, bounded)
│   ├── schemas/            pydantic input contracts + API response models
│   ├── api/                deps, middleware (request id), error handlers, routes
│   ├── seed.py             python -m costlab.seed [--force]
│   └── main.py             app factory
├── alembic/                migrations (0001_initial_schema)
├── tests/                  provider, aggregation, and API tests (39)
├── Dockerfile              pinned python:3.13.1-slim, non-root, healthcheck
└── pyproject.toml          pinned dependencies; ruff/mypy/pytest config
```

## Endpoints

```text
GET /health                    liveness (no DB access)
GET /ready                     readiness (SELECT 1)
GET /api/cost                  paginated cost records + filtered summary
GET /api/cost/trend            daily / weekly / monthly buckets
GET /api/cost/by-service       breakdown by service (share of total)
GET /api/cost/by-project       breakdown by project (share of total)
GET /api/cost/by-environment   breakdown by environment (share of total)
```

Common query filters on every `/api/cost` route: `start_date`, `end_date` (default: data bounds), `project_id`, `service`, `environment`, `region`, `resource_id`. Pagination: `page`, `page_size` (cap 100).

## Run

```bash
# from the repository root
cp .env.example .env
docker compose up -d          # postgres + api; migrations + seeding are automatic
```

Host-run mode with hot reload, migrations, seeding, tests, lint, and type-check commands: [`docs/local-development.md`](../../docs/local-development.md).

## Ground rules

- No credentials in code — configuration via environment variables (see `/.env.example`).
- Every query is bounded; no unbounded datasets over the API; aggregation happens in SQL.
- Demo mode must work with zero GCP access; `Real*` providers fail loudly until Phase 9.
- Money is `Numeric` end-to-end; converted to rounded floats only at the response boundary.
