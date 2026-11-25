# Project Overview — Cloud Cost Lab

## What Is This?

Cloud Cost Lab is a GCP FinOps platform that I built to demonstrate how cloud infrastructure cost relates to resource utilization. It collects billing and usage data, identifies idle and oversized resources, estimates potential savings, monitors budgets, forecasts future costs, and produces evidence-based optimization recommendations.

## Why I Built It

Cloud cost optimization is one of the most impactful problems in infrastructure engineering. Every company running on cloud faces it, yet most engineers lack tooling to connect cost with utilization. I built this to:

1. Demonstrate I can design and implement a production-quality system
2. Show understanding of GCP services, IAM, billing, and monitoring
3. Practice FinOps principles (not just theory, but working code)
4. Build a portfolio piece that maps directly to Cloud/DevOps/SRE job responsibilities

## What It Does

| Capability | Implementation |
|-----------|---------------|
| Cost visibility | Aggregation by service/project/environment/region |
| Resource tracking | 8 resources with CPU, memory, disk, network metrics |
| Waste detection | 5 rules: idle compute, oversized, unused disk, stale storage, anomaly |
| Optimization | Priority scoring, evidence-based savings calculation |
| Forecasting | 30-day projection with confidence range |
| Anomaly detection | Z-score analysis with resource attribution |
| Budget monitoring | Threshold alerts (HEALTHY/WARNING/CRITICAL/EXCEEDED) |
| Governance | 5 policies (labels, cost limits, public access, scheduling) |
| AI advisor | Natural language cost questions (read-only) |
| Savings verification | Lifecycle tracking, before/after measurement |
| Observability | SLI/SLO, metrics, alerting, incident response |

## Technical Highlights

- **329 automated tests** covering business logic, edge cases, and API integration
- **Provider abstraction** (BillingDataProvider, MonitoringDataProvider) for seamless mock/real switching
- **Evidence-based recommendations** — never guesses, always shows data
- **Human approval gates** — no destructive action without explicit approval
- **BigQuery cost safety** — partition-aware queries, column selection, bounded ranges
- **Terraform modules** — IAM, BigQuery, Storage, Compute with least-privilege defaults
- **CI/CD pipeline** — lint, test, security scan (Trivy + Gitleaks), multi-arch Docker build
- **SRE practices** — SLI/SLO, incident docs, runbooks, MTTD/MTTR targets

## What It Demonstrates

For a Cloud Engineer / DevOps / SRE role, this project shows:
- GCP proficiency (Billing, BigQuery, Monitoring, IAM, Terraform)
- System design (modular, testable, observable)
- Security mindset (least-privilege, no credentials in code, scanning)
- Data engineering (aggregation, statistical analysis, forecasting)
- SRE practices (SLI/SLO, incident response, runbooks)
- FinOps understanding (not just monitoring — full optimization lifecycle)
- AI integration (with proper safety constraints)
- Documentation discipline (ADRs, runbooks, setup guides)

## Scale

| Metric | Value |
|--------|-------|
| Backend tests | 329 |
| API endpoints | 30+ |
| Documentation files | 25+ |
| Terraform modules | 4 |
| CI/CD workflows | 3 |
| Incident procedures | 5 |
| Operational runbooks | 5 |
| Architecture decisions | 5 |
| Recommendation rules | 5 |
| Governance policies | 5 |
