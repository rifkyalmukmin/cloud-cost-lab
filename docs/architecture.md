# Architecture — Cloud Cost Lab

## Overview

Cloud Cost Lab is a modular FinOps platform that collects cloud cost and utilization data, analyzes efficiency, and produces actionable recommendations with human approval gates.

## Design Principles

1. **GCP-first** — optimized for Google Cloud Platform, extensible toward multi-cloud
2. **Small and understandable** — suitable for a single engineer to operate
3. **Modular** — each component has a clear boundary and can evolve independently
4. **Safe by default** — no destructive actions without human approval
5. **Data-driven** — all recommendations backed by observed metrics
6. **Cost-aware** — the platform itself must not become expensive
7. **Observable** — structured logging, metrics, health checks
8. **Testable** — business logic covered by automated tests

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Billing    │  │  Cloud       │  │   Cloud      │  │
│  │   Export     │  │  Monitoring  │  │   Logging    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          └──────────┬───────┴──────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   Data Collector Layer                    │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ RealBillingProvider│  │  MockBillingProvider        │ │
│  └──────────┬───────┘  └──────────┬──────────────────┘ │
│             └───────────┬──────────┘                     │
│                         ▼                                │
│              BillingDataProvider (interface)              │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                    │
│                                                          │
│  cost_records | resources | resource_usage | budgets     │
│  recommendations | savings | anomalies | forecast_runs   │
│  policies | audit_logs                                   │
└─────────────────────────┬───────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Cost         │ │ Usage        │ │ Recommendation│
│ Analytics    │ │ Analytics    │ │ Engine        │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────┬───────┴────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  /api/cost | /api/resources | /api/recommendations       │
│  /api/forecast | /api/budget | /api/anomalies            │
│  /api/savings | /api/finops-score                        │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Next.js Frontend                        │
│                                                          │
│  Dashboard | Cost Explorer | Resources | Recommendations │
│  Forecast | Budget | Utilization | AI Advisor            │
└─────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Data Collector
- Fetches billing data from GCP Billing Export (BigQuery) or mock provider
- Fetches utilization metrics from Cloud Monitoring or mock provider
- Normalizes data into internal schema
- Stores in PostgreSQL

### Cost Analytics
- Aggregates costs by project, service, region, environment, date
- Computes MoM/WoW changes
- Identifies top spenders
- Detects unallocated costs

### Usage Analytics
- Correlates resource utilization with cost
- Identifies idle resources (low CPU/memory/network over time)
- Identifies overprovisioned resources

### Recommendation Engine
- Rule-based engine with pluggable rules
- Each rule: evaluate(), explain(), calculate_saving(), calculate_risk()
- Rules: IdleCompute, OversizedCompute, UnusedDisk, StorageRetention, etc.
- Lifecycle: OPEN → APPROVED → IMPLEMENTED → VERIFIED

### Forecasting
- Moving average and linear regression
- 30-day projection with confidence range
- Budget breach prediction

### Anomaly Detection
- Rolling average + threshold comparison
- Z-score analysis
- Alerts with attribution (which service/resource caused the spike)

### AI Advisor
- Read-only LLM integration
- Structured context injection (costs, utilization, recommendations)
- Human-readable analysis and prioritization
- No direct resource modification capability

## Data Flow

```
GCP Billing Export (BigQuery)
        │
        ▼
  Data Collector (scheduled)
        │
        ▼
  PostgreSQL (normalized cost_records, resources, usage)
        │
        ├──► Cost Analytics ──► Trend, Aggregation, Anomaly
        │
        ├──► Usage Analytics ──► Utilization, Idle Detection
        │
        ├──► Recommendation Engine ──► Prioritized Recommendations
        │
        ├──► Forecasting ──► 30-day Projection
        │
        └──► Budget Engine ──► Budget Status, Alerts
                │
                ▼
          FastAPI (REST API)
                │
                ▼
          Next.js (Dashboard)
```

## Deployment Topology

### Local Development (Docker Compose)
- PostgreSQL container
- FastAPI container (hot reload)
- Next.js dev server
- Demo mode (no GCP required)

### Production (GCP)
- Cloud Run or Compute Engine for API
- Cloud SQL for PostgreSQL
- Artifact Registry for container images
- Secret Manager for credentials
- IAM with least-privilege service accounts

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monorepo | Yes | Simpler for single-engineer project |
| API framework | FastAPI | Async, validation, auto-docs |
| Frontend | Next.js | SSR, routing, TypeScript |
| Database | PostgreSQL | Reliable, well-supported, sufficient for this scale |
| IaC | Terraform | Industry standard, GCP provider mature |
| Mock mode | Required | Must work without GCP credentials |
| AI safety | Read-only | No destructive actions without human approval |

## Security Architecture

```
┌─────────────────────────────────────────┐
│              IAM Boundary                │
│                                          │
│  cost-data-reader    (Billing read)      │
│  monitoring-reader   (Metrics read)      │
│  cost-optimizer      (Limited write)     │
│                                          │
│  Workload Identity Federation            │
│  (no static keys in CI/CD)              │
└─────────────────────────────────────────┘
```

- Separate service accounts per responsibility
- No broad Owner/Editor roles
- Secrets in Secret Manager, not env files in production
- Trivy + Gitleaks in CI pipeline

## Scalability Path

Current scope: single GCP project, single engineer.

Future extensions (not in current scope):
- Multi-project aggregation
- Multi-cloud (AWS, Azure) via additional providers
- Event-driven pipeline (Pub/Sub) for real-time cost events
- GKE/Cloud Run optimization modules
