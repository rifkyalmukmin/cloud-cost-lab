# Cloud Cost Lab

**GCP FinOps & Cloud Cost Optimization Platform**

---

## Problem

Cloud infrastructure costs grow unpredictably. Engineers provision resources but rarely monitor utilization or cost efficiency. Without visibility, waste accumulates — idle VMs run 24/7, oversized instances serve minimal traffic, unattached disks persist indefinitely, and budgets are exceeded without warning.

## Solution

Cloud Cost Lab aggregates cloud cost and resource utilization data, detects waste and optimization opportunities, estimates potential savings, monitors budgets, forecasts future cost, and provides evidence-based recommendations with human approval before impactful actions.

## Architecture

```
                   GCP
                    |
            +-------+-------+
            |               |
            v               v
      Billing Export     Monitoring
            |               |
            +-------+-------+
                    |
                    v
             Data Collector
                    |
                    v
              Cost Database
                    |
          +---------+---------+
          |                   |
          v                   v
    Cost Analytics      Usage Analytics
          |                   |
          +---------+---------+
                    |
                    v
             Recommendation
                 Engine
                    |
        +-----------+-----------+
        |                       |
        v                       v
  Rule-based Engine           AI Layer
        |                       |
        +-----------+-----------+
                    |
                    v
              Cost Dashboard
                    |
          +---------+---------+
          |         |         |
          v         v         v
       Costs    Savings    Forecast
                    |
                    v
                 Alerts
                    |
                    v
             Human Approval
                    |
                    v
             Optional Action
```

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui | Modern React framework with type safety |
| Backend | FastAPI + Python + Pydantic | Fast async API with automatic validation |
| Database | PostgreSQL | Reliable relational store for cost/resource data |
| Cloud | Google Cloud Platform | Billing Export, BigQuery, Monitoring, IAM |
| IaC | Terraform | Declarative infrastructure management |
| CI/CD | GitHub Actions | Native integration, free tier for public repos |
| Security | Trivy, Gitleaks, Secret Manager | Multi-layer security scanning |
| Observability | Cloud Monitoring, Cloud Logging | Native GCP observability |
| AI | Pluggable LLM (read-only) | Cost analysis assistance |

## Key Features

- **Cost Explorer** — filter and group costs by project, service, region, environment
- **Resource Inventory** — track all cloud resources with utilization metrics
- **Idle Detection** — identify underutilized resources with evidence
- **Rightsizing** — recommend optimal instance sizes based on observed usage
- **Budget Monitoring** — track spend against budgets with alerts
- **Cost Forecasting** — project future costs with confidence ranges
- **Anomaly Detection** — flag unexpected cost spikes
- **Savings Tracking** — distinguish potential vs realized savings
- **FinOps Score** — heuristic health score across visibility, allocation, optimization
- **AI Advisor** — read-only LLM-powered cost analysis assistant
- **Policy Engine** — enforce cost governance rules
- **Human Approval** — no destructive action without explicit approval

## Operating Modes

### Demo Mode (`DEMO_MODE=true`)
Works without GCP credentials using synthetic data. Full dashboard and recommendation engine functional.

### Real Mode
Connects to GCP Billing Export via BigQuery. Requires configured service account with least-privilege IAM.

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

Frontend: http://localhost:3000
API: http://localhost:8000
API Docs: http://localhost:8000/docs

## Project Structure

```
cloud-cost-lab/
├── apps/
│   ├── api/          # FastAPI backend
│   └── web/          # Next.js frontend
├── analytics/        # Cost & utilization analysis modules
├── data/
│   └── mock/         # Synthetic demo data
├── terraform/        # Infrastructure as Code
│   ├── modules/
│   └── environments/
├── monitoring/       # Observability configs
├── scripts/          # Utility scripts
├── docs/             # Documentation
│   ├── decisions/    # Architecture Decision Records
│   ├── reports/      # Generated reports
│   └── incidents/    # Incident documentation
├── .github/
│   └── workflows/    # CI/CD pipelines
├── docker-compose.yml
├── .env.example
└── CLAUDE.md
```

## Cost Safety

This project follows strict cost safety rules:
- No unbounded BigQuery queries
- No silent creation of expensive resources
- Budget alerts configured before resource creation
- All Terraform changes reviewed before apply
- Mock mode as default for development

See [docs/cost-safety.md](docs/cost-safety.md) for details.

## Security

- Least-privilege IAM
- No credentials in source code
- Secret Manager for sensitive values
- Workload Identity Federation where feasible
- Trivy + Gitleaks in CI/CD

See [docs/security.md](docs/security.md) for details.

## Current Phase

**Phase 8 — GCP Billing Integration** (Complete)

- BillingDataProvider abstraction (interface for mock and real GCP data)
- MockBillingProvider (default, no GCP needed)
- GCPBillingProvider (BigQuery Billing Export, opt-in)
- Partition-aware, cost-safe BigQuery queries (no SELECT *, bounded dates, column-specific)
- Data freshness tracking (FRESH/STALE/UNKNOWN) with /data-freshness endpoint
- Provider factory with DEMO_MODE toggle
- 209 backend tests passing (includes provider error handling, auth failures)
- GCP setup guide, BigQuery cost documentation
- No GCP resources created — code only

See [docs/project-roadmap.md](docs/project-roadmap.md) for the full roadmap.

## Limitations

- Project-specific heuristics, not industry-standard benchmarks
- Forecasting uses simple models (moving average, linear regression)
- AI is read-only — cannot take destructive actions
- Single-cloud (GCP) initially; multi-cloud is future work
- Cost data freshness depends on GCP Billing Export lag (~24h)

## License

Private project — portfolio demonstration.
