# Local Development — Cloud Cost Lab (Phase 1)

> Target machine: MacBook Pro M1 / 8 GB RAM / macOS. Everything here runs locally with **zero GCP credentials and zero cloud cost**.

---

## 1. Prerequisites

| Tool | Version | Check |
| --- | --- | --- |
| Python | ≥ 3.12 (developed on 3.13) | `python3 --version` |
| Docker (Docker Desktop or OrbStack) | any recent | `docker compose version` |

Nothing else. PostgreSQL runs in Docker; the API runs either in Docker or on your host.

## 2. Quick start (Docker, recommended)

```bash
cp .env.example .env          # local config; .env is git-ignored
docker compose up -d          # postgres + api
```

The `api` container automatically runs migrations (`alembic upgrade head`), seeds the deterministic mock dataset (idempotent — a no-op if data exists), and starts uvicorn.

- API: http://localhost:8000 (docs at `/docs`)
- Health: `curl localhost:8000/health` · Readiness: `curl localhost:8000/ready`

> Port conflict? If another local project already uses 5432/8000, set `POSTGRES_PORT` / `API_PORT` in `.env` — the compose file maps them to the *host* side only; container-internal ports stay fixed.

## 3. Quick start (host-run API, hot reload)

Keep only postgres in Docker, run the API on your host:

```bash
cp .env.example .env
docker compose up -d postgres

python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[dev]'

.venv/bin/alembic -c apps/api/alembic.ini upgrade head   # create schema
.venv/bin/python -m costlab.seed                          # load mock data (idempotent)
.venv/bin/uvicorn costlab.main:app --reload --port 8000   # from repo root
```

Config comes from environment variables and the repo-root `.env` (see `.env.example`). Nothing is hardcoded.

## 4. Commands

| Task | Command |
| --- | --- |
| Apply migrations | `.venv/bin/alembic -c apps/api/alembic.ini upgrade head` |
| Seed mock data (idempotent) | `.venv/bin/python -m costlab.seed` |
| Replace seeded demo data | `.venv/bin/python -m costlab.seed --force` (demo mode only) |
| Regenerate mock dataset | `.venv/bin/python scripts/generate_mock_data.py` (deterministic; review the diff!) |
| Run tests | `.venv/bin/python -m pytest apps/api` |
| Lint | `.venv/bin/ruff check apps/api scripts` |
| Format | `.venv/bin/ruff format apps/api scripts` |
| Type check | `.venv/bin/mypy apps/api/src` |

## 5. Tests

Tests create a dedicated database `cloud_cost_lab_test` (name derived from `POSTGRES_DB`), apply migrations, seed the same committed mock dataset, run, and drop the database. They therefore need the docker postgres running:

```bash
docker compose up -d postgres
.venv/bin/python -m pytest apps/api
```

- Aggregation tests recompute expected values independently from `data/mock/cost.json` in plain Python — SQL aggregations are checked against a second implementation, not against themselves.
- The mock dataset is deterministic (fixed seeds), so tests never flake on data.

## 6. Mock data workflow

The JSON files in `data/mock/` are **committed source data**. Re-run the generator only when intentionally changing scenarios:

```bash
.venv/bin/python scripts/generate_mock_data.py
git diff data/mock/          # review the deterministic diff
```

Regeneration is byte-identical unless the generator logic changed — that is the point (ADR-003).

## 7. Troubleshooting

- **`Mock data file not found: .../cost.json`** — the committed dataset is missing; run the generator (§6).
- **`password authentication failed`** — your `.env` password does not match the one postgres was first initialized with. Simplest fix: `docker compose down -v && docker compose up -d` (wipes the local demo volume — safe, data is re-seeded).
- **Port already allocated** — another project's container owns the port; change `POSTGRES_PORT`/`API_PORT` in `.env`.
- **Module `costlab` not found** — the editable install was made before `apps/api/src/costlab` existed; re-run `.venv/bin/pip install -e 'apps/api[dev]'`.
- **M1 / ARM note** — all images and wheels used support `linux/arm64` and `darwin/arm64` natively.

## 8. Resource footprint

Default stack: one postgres container (~50 MB RAM) + one uvicorn process. Well within the 8 GB laptop budget; no Kubernetes, no local LLM, no other containers required.
