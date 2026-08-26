# Cloud Cost Lab

**GCP FinOps & Cloud Cost Optimization Platform**

A comprehensive platform that helps engineers understand where cloud money goes, detect waste, forecast costs, and optimize infrastructure with evidence-based recommendations and human approval gates.

---

## Problem

Cloud infrastructure costs grow unpredictably. Engineers provision resources but rarely monitor utilization or cost efficiency. Without visibility:

- Idle VMs run 24/7 costing hundreds per month
- Oversized instances serve minimal traffic
- Unattached disks persist indefinitely
- Budgets are exceeded without warning
- No one knows which team owns which cost

## Solution

Cloud Cost Lab aggregates cloud cost and resource utilization data, detects waste and optimization opportunities, estimates potential savings, monitors budgets, forecasts future costs, and provides evidence-based recommendations — all with human approval before impactful actions.

## Architecture

```
                   GCP
                    |
            +-------+-------+
            |               |
            v               v
      Billing Export     Monitoring
      (BigQuery)        (Metrics API)
            |               |
            +-------+-------+
                    |
                    v
          BillingDataProvider
          MonitoringDataProvider
                    |
                    v
             FastAPI Backend
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
  Cost Analytics  Utilization  Recommendation
                  Analysis     Engine (5 rules)
        |           |           |
        +-----------+-----------+
                    |
        +-----------+-----------+-----------+
        |           |           |           |
        v           v           v           v
    Forecast    Anomaly     Budget      AI Advisor
    Engine      Detection   Monitor     (read-only)
        |           |           |           |
        +-----------+-----------+-----------+
                    |
                    v
             Next.js Dashboard
                    |
           Human Approval Gate
                    |
              Audit Log
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16 + TypeScript + Tailwind + shadcn/ui | Cost dashboard with interactive charts |
| Backend | FastAPI + Python + Pydantic | REST API with validation and auto-docs |
| Database | PostgreSQL | Cost and resource data storage |
| Cloud | Google Cloud Platform | Billing Export, BigQuery, Monitoring, IAM |
| IaC | Terraform (4 modules) | Declarative infrastructure management |
| CI/CD | GitHub Actions (3 workflows) | Lint, test, security scan, Docker build |
| Security | Trivy + Gitleaks + IAM | Multi-layer scanning, least-privilege |
| Observability | SLI/SLO + metrics + structured logs | Operational reliability |
| AI | Rule-based + pluggable LLM | Read-only cost analysis assistant |

## Key Capabilities

### Cost Visibility
- Cost breakdown by service, project, environment, region
- Daily/weekly/monthly cost trends
- Month-over-month change tracking
- Data freshness monitoring (FRESH/STALE/UNKNOWN)

### Resource Efficiency
- Resource inventory with CPU, memory, disk, network metrics
- Utilization pattern detection (low, high, unstable, missing)
- Evidence strength assessment (STRONG/MODERATE/WEAK/INSUFFICIENT)
- Cost-vs-utilization correlation (scatter plot)

### Optimization
- 5 recommendation rules: IdleCompute, OversizedCompute, UnusedDisk, StorageRetention, CostAnomaly
- Priority scoring (savings × confidence ÷ risk)
- Lifecycle: OPEN → APPROVED → IMPLEMENTED → VERIFIED
- Potential vs realized savings distinction

### Forecasting & Anomaly Detection
- 30-day hybrid forecast (linear trend + moving average)
- Confidence ranges (never presented as exact values)
- Z-score anomaly detection with attribution (which service/resource caused it)

### Budget & Governance
- Budget monitoring with threshold alerts (HEALTHY/WARNING/CRITICAL/EXCEEDED)
- 5 governance policies (owner labels, environment tags, cost limits, public access, scheduling)
- Policy evaluation: PASS/WARNING/VIOLATION

### AI Advisor
- Natural language questions about cloud costs
- READ-ONLY (cannot take destructive actions)
- Structured responses with evidence, risk, and confidence
- Prompt injection protection and sensitive data filtering

### Observability & SRE
- Application metrics (requests, latency, freshness)
- SLI/SLO compliance (API 99.5%, freshness <24h, recommendations 99%)
- 5 alerting rules with runbooks
- 5 incident response procedures (MTTD/MTTR targets)

## Demo

### Quick Start (Demo Mode — no GCP needed)

```bash
# Backend
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# Frontend
cd apps/web
npm install && npm run dev
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### With Docker

```bash
docker compose up -d
```

### Demo Flow (5 minutes)

1. **Overview** (`/`) — Monthly cost, MoM change, projected cost, potential savings
2. **Cost Explorer** (`/cost`) — Daily trend chart, service/project/environment breakdown
3. **Resources** (`/resources`) — 8 resources with utilization bars, click for detail
4. **Recommendations** (`/recommendations`) — Prioritized optimization cards with evidence
5. **Utilization** (`/utilization`) — Cost vs CPU scatter plot, pattern analysis
6. **AI Advisor** (`POST /api/ai/ask`) — "Where can I save money?"
7. **Savings** (`GET /api/savings`) — Potential vs realized, audit log

## FinOps Workflow

```
Detect → Recommend → Approve → Implement → Measure → Verify

1. Cost data collected (GCP Billing Export or mock)
2. Utilization analyzed (CPU, memory, disk, connections)
3. Rules evaluate resources against thresholds
4. Recommendations generated with evidence and priority
5. Human reviews and approves (or rejects with reason)
6. Engineer implements the change
7. System verifies actual savings with before/after data
8. Audit log records every decision
```

## Security

- **Least-privilege IAM**: cost-reader (BQ viewer + job user), monitoring-reader (viewer)
- **No credentials in code**: environment variables, .gitignore blocks all key files
- **Workload Identity Federation**: preferred over JSON keys for production
- **Trivy + Gitleaks**: filesystem + Docker image scanning in CI
- **AI read-only**: cannot modify infrastructure
- **Human approval gates**: no destructive action without explicit approval
- **Sensitive data filtering**: keys, tokens, credentials never reach AI context

## SRE Practices

| SLI | Target | Description |
|-----|--------|-------------|
| API availability | ≥ 99.5% | Successful responses / total requests |
| Data freshness | < 24 hours | Time since last billing data update |
| Recommendation success | ≥ 99% | Engine completions without error |

Incidents documented: billing stale, BigQuery failure, API outage, recommendation failure, forecast failure. Each with MTTD target, MTTR target, and operational runbook.

## Testing

- **312 backend tests** (unit + integration)
- Coverage: cost aggregation, utilization statistics, recommendation boundaries, lifecycle enforcement, AI safety, SLI/SLO
- Frontend: TypeScript strict mode + ESLint + build validation

## Cost Safety

This project practices what it preaches:
- Demo mode as default (zero GCP cost)
- BigQuery queries: partition-filtered, column-specific, bounded dates
- Terraform: smallest instances, preemptible, lifecycle policies
- Estimated self-cost: $0.05/month (dev) to $4/month (with compute)

## Limitations

- Project-specific heuristics, not industry-standard benchmarks
- Forecasting uses simple models (moving average, linear regression)
- AI is read-only — recommends but cannot execute
- Single-cloud (GCP) initially; multi-cloud is future architecture
- Cost data freshness depends on GCP Billing Export lag (~24h)
- Mock data for demo (real GCP integration is opt-in)

## Future Roadmap

- Multi-cloud support (AWS, Azure providers)
- FinOps score (visibility, allocation, optimization, governance dimensions)
- Cost reports generation (daily/weekly/monthly)
- Kubernetes (GKE) cost optimization
- Cloud Run optimization
- Real-time cost alerting (Pub/Sub)
- Team-level cost allocation dashboards
- Savings trend visualization over time

## Documentation

```
docs/
├── architecture.md           # System design and component diagram
├── cost-model.md             # How costs are aggregated
├── cost-safety.md            # BigQuery and GCP cost protection
├── bigquery-cost.md          # Query optimization patterns
├── resource-inventory.md     # Resource tracking design
├── utilization-analysis.md   # Metrics and pattern detection
├── recommendation-engine.md  # Rules, priority, lifecycle
├── savings.md                # Potential vs realized savings
├── forecasting.md            # Forecast methodology
├── anomaly-detection.md      # Z-score analysis
├── budget.md                 # Budget monitoring
├── governance.md             # Policy engine
├── ai-advisor.md             # AI safety and capabilities
├── gcp-billing.md            # Billing Export integration
├── gcp-monitoring.md         # Cloud Monitoring integration
├── gcp-setup.md              # Step-by-step GCP setup
├── terraform.md              # Infrastructure as Code
├── infrastructure-cost.md    # Self-cost analysis
├── local-development.md      # Dev environment setup
├── dashboard.md              # Frontend documentation
├── project-roadmap.md        # Phase plan
├── decisions/                # Architecture Decision Records (5 ADRs)
├── incidents/                # Incident response docs (5)
├── runbooks/                 # Operational runbooks (5)
└── portfolio/                # CV, LinkedIn, interview prep
```

## License

Private project — portfolio demonstration.
