# Local Development — Cloud Cost Lab

## Prerequisites

- Python 3.11+ (tested with 3.13)
- Docker & Docker Compose (for PostgreSQL, optional in Phase 1)
- Node.js 18+ (for frontend, Phase 2)

## Quick Start (API only, Demo Mode)

```bash
cd apps/api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --port 8000
```

API available at: http://localhost:8000
API docs at: http://localhost:8000/docs

## With Docker Compose

```bash
# Start all services
docker compose up -d

# Check health
curl http://localhost:8000/health
```

## Environment Variables

Copy the template:
```bash
cp .env.example .env
```

Key variables:
| Variable | Default | Description |
|----------|---------|-------------|
| DEMO_MODE | true | Use synthetic data (no GCP needed) |
| APP_ENV | development | Environment name |
| API_PORT | 8000 | API server port |
| DATABASE_URL | postgresql://... | PostgreSQL connection |
| LOG_LEVEL | INFO | Logging level |

## Running Tests

```bash
cd apps/api
source .venv/bin/activate

# Run all tests
pytest

# Verbose output
pytest -v

# Specific test file
pytest tests/test_cost_service.py
```

## Project Structure

```
apps/api/
├── app/
│   ├── main.py           # FastAPI application entry
│   ├── config.py         # Settings (env-based)
│   ├── models/
│   │   ├── database.py   # SQLAlchemy models
│   │   └── schemas.py    # Pydantic response schemas
│   ├── routers/
│   │   ├── health.py     # /health, /ready
│   │   └── cost.py       # /api/cost/*
│   ├── services/
│   │   ├── mock_data.py  # Deterministic data generator
│   │   └── cost_service.py  # Cost analytics logic
│   └── db/               # Database utilities (future)
├── tests/
│   ├── test_api.py       # API integration tests
│   └── test_cost_service.py  # Unit tests
├── requirements.txt
├── Dockerfile
└── pytest.ini
```

## Resource Usage

The API in demo mode uses minimal resources:
- ~30MB RAM
- No database connection required
- No network calls to GCP

Safe for MacBook with 8GB RAM.
