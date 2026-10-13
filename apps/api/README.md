# apps/api — Backend API

FastAPI + Python (Pydantic, SQLAlchemy, Alembic) backend for Cloud Cost Lab.

**Status: implemented.** Serves cost analytics, resource inventory, utilization,
the recommendation engine with an approval/savings lifecycle, budgets and
policies, forecast and anomaly detection, observability endpoints and a
read-only AI advisor. Runs on PostgreSQL, loaded from the deterministic mock
dataset (`DEMO_MODE=true`) with no GCP access. The BigQuery billing and Cloud
Monitoring providers are implemented and tested but dormant in demo mode (they
need real credentials and are not exercised by the demo).

## Layout

```text
apps/api/
├── src/costlab/
│   ├── config.py           settings from environment variables (.env supported)
│   ├── logging_config.py   structured JSON logs + request-id context var
│   ├── db/                 engine, session factory, SQLAlchemy models
│   ├── providers/          BillingDataProvider / UsageDataProvider: mock, gcp (BigQuery), monitoring
│   ├── ingestion/          snapshot validation + loader (idempotent seeding)
│   ├── analytics/          cost, resources, utilization, budget, forecasting, anomalies,
│   │                       savings, freshness, observability (SQL aggregation, bounded)
│   ├── recommendations/    pluggable rule engine (rules.py, engine.py, base.py)
│   ├── governance/         policies + audit log
│   ├── ai/                 read-only advisor (mock provider, optional OpenAI-compatible)
│   ├── schemas/            pydantic input contracts + API response models
│   ├── api/                deps, middleware (request id, metrics), error handlers,
│   │                       auth (X-API-Key), routes_*.py
│   ├── seed.py             python -m costlab.seed [--force]
│   └── main.py             app factory
├── alembic/                migrations (versions/0001 … 0005 at the time of writing)
├── tests/                  pytest suite (providers, aggregations, API, auth, rules, savings, …)
├── Dockerfile              multi-stage, pinned python:3.13.1-slim-bookworm, non-root, healthcheck
├── entrypoint.sh           alembic upgrade head → python -m costlab.seed → exec CMD
└── pyproject.toml          pinned dependencies; ruff/mypy/pytest config
```

## Endpoints

Interactive docs: `http://localhost:8000/docs` (OpenAPI). Lists are paginated
(`page`, `page_size`, cap 100).

```text
# platform
GET  /health                              liveness (no DB access)
GET  /ready                               readiness (SELECT 1)
GET  /metrics                             Prometheus text format
GET  /api/freshness                       billing data freshness (FRESH / STALE)
GET  /api/reliability                     SLI/SLO status
GET  /api/alerts                          in-process alert evaluation

# cost
GET  /api/cost                            paginated cost records + filtered summary
GET  /api/cost/trend                      daily / weekly / monthly buckets
GET  /api/cost/by-service | by-project | by-environment

# resources & utilization
GET  /api/resources, /api/resources/{id}
GET  /api/utilization, /api/utilization/{resource_id}

# recommendations & savings
GET  /api/recommendations, /api/recommendations/{id}
GET  /api/recommendations/savings         potential vs verified savings summary
GET  /api/recommendations/audit-logs
POST /api/recommendations/run             run the rule engine            (X-API-Key)
POST /api/recommendations/{id}/approve    OPEN → APPROVED                (X-API-Key)
POST /api/recommendations/{id}/reject                                    (X-API-Key)
POST /api/recommendations/{id}/implement  APPROVED → IMPLEMENTED         (X-API-Key)
POST /api/recommendations/{id}/verify     measure → VERIFIED             (X-API-Key)

# governance, forecast, anomalies
GET  /api/budget                          budgets + status
POST /api/budget                          create a budget                (X-API-Key)
GET  /api/policies                        policy results (PASS / WARNING / VIOLATION)
GET  /api/forecast                        30-day (7–90) forecast with a range
GET  /api/anomalies                       rolling-average / z-score anomalies

# AI advisor (read-only)
GET  /api/ai/status
POST /api/ai/advisor
```

`/api/cost` routes share the filters `start_date`, `end_date` (default: data
bounds), `project_id`, `service`, `environment`, `region`, `resource_id`.
Recommendation lists filter by `status`, `rule_id`, `risk`, `priority`,
`resource_id`, `project_id` and sort by `priority | savings | recent`.

## Authentication (write endpoints)

Every state-changing recommendation/budget endpoint requires an `X-API-Key`
header. `API_KEYS` holds comma-separated `name:key` pairs (key ≥ 16 characters);
the name is recorded as the audit-log actor. With `API_KEYS` empty, every write
is rejected (fail closed). Read endpoints and the read-only AI advisor do not
require a key. Details: [`docs/security.md`](../../docs/security.md).

```bash
echo "API_KEYS=me:$(openssl rand -hex 24)" >> .env
curl -X POST -H "X-API-Key: <key>" http://localhost:8000/api/recommendations/run
```

**Rate limiting:** being added in a separate change (`RATE_LIMIT_PER_MINUTE`).
Check `.env.example` and `src/costlab/config.py` after it lands; this README does
not describe it until then.

## Configuration

All values come from environment variables (or the repo-root `.env`); see
[`/.env.example`](../../.env.example). Defaults in `src/costlab/config.py`.

| Variable | Purpose |
| --- | --- |
| `DEMO_MODE` | `true` (default): synthetic data, no GCP. `false`: real GCP providers |
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` or `DATABASE_URL` | database connection (placeholder password is local-only) |
| `API_KEYS` | write-endpoint credentials (see above) |
| `CORS_ORIGINS` | browser origins allowed to call the API (default `http://localhost:3000`) |
| `LOG_LEVEL` | structured JSON log level |
| `FRESHNESS_MAX_HOURS` | age after which billing data is labelled `STALE` |
| `GCP_BILLING_PROJECT/DATASET/TABLE/LOCATION`, `GCP_BILLING_MAX_DAYS/MAX_ROWS` | BigQuery billing export (real mode only; bounded queries) |
| `GCP_MONITORING_PROJECT`, `GCP_MONITORING_MAX_DAYS/MAX_AGE_DAYS` | Cloud Monitoring usage metrics (real mode only) |
| `AI_PROVIDER` (`mock` \| `openai-compatible`), `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` | AI advisor provider; default is the offline mock |

## Run

```bash
# from the repository root
cp .env.example .env
docker compose up -d          # postgres + api; migrations + seeding are automatic
```

Host-run mode with hot reload, migrations, seeding, tests, lint and type-check
commands: [`docs/local-development.md`](../../docs/local-development.md).

```bash
# quality gates (what CI runs from apps/api/; pytest needs the postgres container)
pip install -e '.[dev]'
ruff check . && ruff format --check .
mypy src/costlab
pytest
```

### Docker image

Build from the **repository root** (the context includes `data/mock`):

```bash
DOCKER_BUILDKIT=1 docker build -f apps/api/Dockerfile -t cloud-cost-lab-api .
```

Multi-stage (builder venv with a BuildKit pip cache mount → slim runtime), pinned
base tag, non-root uid 10001, healthcheck on `/health`, no secrets baked in
(`.dockerignore` excludes `.env`, keys and state files). The optional `gcp` extra
(`google-cloud-bigquery`) is **not** installed in the image, so real BigQuery mode
needs a host install (`pip install -e '.[gcp]'`) or an image change.

## Ground rules

- No credentials in code — configuration via environment variables.
- Every query is bounded; no unbounded datasets over the API; aggregation happens in SQL.
- Demo mode must work with zero GCP access; the GCP providers fail loudly with
  actionable errors rather than serving partial data.
- Money is `Numeric` end-to-end; converted to rounded floats only at the response boundary.
- Savings are *potential* until a post-change verification (`/verify`) observes real data.
