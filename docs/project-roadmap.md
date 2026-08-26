# Project Roadmap — Cloud Cost Lab

## Phase Overview

| Phase | Title | Status | Description |
|-------|-------|--------|-------------|
| 0 | Foundation & Architecture | Complete | Repository structure, architecture, ADRs |
| 1 | Local Mock Platform | Pending | FastAPI + PostgreSQL + demo data |
| 2 | Cost Explorer | Pending | Aggregation, charts, filters |
| 3 | Resource Inventory | Pending | Resources, usage, cost linkage |
| 4 | Recommendation Engine | Pending | Idle, rightsizing, storage rules |
| 5 | Budget | Pending | Budget monitoring and alerts |
| 6 | Forecasting | Pending | 30-day forecast with confidence range |
| 7 | Anomaly Detection | Pending | Cost spike detection |
| 8 | Savings Tracking | Pending | Potential vs realized savings |
| 9 | GCP Integration | Pending | Billing Export + BigQuery |
| 10 | Monitoring / Data Freshness | Pending | GCP Monitoring/Logging integration |
| 11 | Terraform | Pending | Infrastructure as Code |
| 12 | Security | Pending | IAM, secrets, scanning |
| 13 | CI/CD | Pending | GitHub Actions pipeline |
| 14 | FinOps Score | Pending | Heuristic health score |
| 15 | Reports | Pending | Daily/weekly/monthly reports |
| 16 | AI Advisor | Pending | Read-only LLM cost assistant |
| 17 | Demo Scenarios | Pending | Synthetic incident/cost scenarios |
| 18 | Portfolio Preparation | Pending | README, screenshots, demo, CV |

## Phase Details

### Phase 0 — Foundation & Architecture
- Repository structure
- Architecture documentation
- Technology decisions (ADRs)
- Cost safety strategy
- Security strategy
- Data model definition
- Project roadmap

### Phase 1 — Local Mock Platform
- FastAPI application scaffold
- PostgreSQL schema (migrations)
- Mock data provider
- Docker Compose setup
- Health/ready endpoints
- Basic API structure

### Phase 2 — Cost Explorer
- Cost aggregation by dimensions (service, project, region, environment)
- Date range filtering
- Daily/weekly/monthly cost views
- MoM/WoW change calculation
- Next.js frontend with charts

### Phase 3 — Resource Inventory
- Resource tracking (Compute, Storage, SQL, etc.)
- Utilization metrics (CPU, memory, disk, network)
- Cost attribution per resource
- Resource status tracking

### Phase 4 — Recommendation Engine
- Pluggable rule architecture
- IdleComputeRule
- OversizedComputeRule
- UnusedDiskRule
- StorageRetentionRule
- Recommendation lifecycle (OPEN → APPROVED → IMPLEMENTED → VERIFIED)
- Evidence-based output

### Phase 5 — Budget
- User-defined budgets
- Budget utilization tracking
- Warning/critical/exceeded thresholds
- Projected month-end spend

### Phase 6 — Forecasting
- Moving average
- Linear regression
- 30-day projection
- Confidence range
- Budget breach prediction

### Phase 7 — Anomaly Detection
- Rolling average + threshold
- Z-score analysis
- Service/resource attribution
- Alert generation

### Phase 8 — Savings Tracking
- Potential savings (estimated before action)
- Realized savings (verified after action)
- Savings by category
- Savings trend over time

### Phase 9 — GCP Integration
- Billing Export to BigQuery setup guide
- BigQuery query cost protection
- Real billing data provider
- Credential management

### Phase 10 — Monitoring / Data Freshness
- Data freshness tracking
- Stale data alerts
- Cloud Monitoring integration
- Cloud Logging integration

### Phase 11 — Terraform
- Module: billing export
- Module: service accounts
- Module: BigQuery dataset
- Module: storage
- Environment configs (dev, demo)

### Phase 12 — Security
- Least-privilege service accounts
- Secret Manager integration
- Trivy scanning
- Gitleaks scanning
- Workload Identity Federation guide

### Phase 13 — CI/CD
- Lint + test
- Build
- Security scan
- Docker build + push
- Terraform validate

### Phase 14 — FinOps Score
- Visibility dimension
- Allocation dimension
- Optimization dimension
- Governance dimension
- Forecasting dimension
- Automation dimension
- Composite heuristic score

### Phase 15 — Reports
- Daily cost report
- Weekly summary
- Monthly executive report
- Markdown + optional HTML output

### Phase 16 — AI Advisor
- Pluggable LLM provider
- Structured context injection
- Cost analysis questions
- Read-only safety model
- Audit logging

### Phase 17 — Demo Scenarios
- Idle VM scenario
- Oversized VM scenario
- Cost spike scenario
- Budget risk scenario
- Unused disk scenario
- Development scheduling scenario

### Phase 18 — Portfolio Preparation
- Screenshots
- Demo script
- Interview preparation document
- CV description
- Architecture diagram (visual)
- Lessons learned

## Definition of Done

A feature is complete when:
- Code exists and works
- Tests cover business logic
- Validation passes (lint, type check, tests)
- Documentation exists
- Error handling is implemented
- Security implications reviewed
- Cost implications considered
- Failure mode is documented
- UI/API behavior verified (when applicable)
- Observability added (when appropriate)
