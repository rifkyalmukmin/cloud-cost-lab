# CLAUDE.md — Cloud Cost Lab

> **GCP FinOps & Cloud Cost Optimization Platform**
>
> Project portfolio untuk mahasiswa Informatika semester 4 yang menargetkan karier Cloud Engineer, DevOps Engineer, Infrastructure Engineer, SRE, Platform Engineer, dan Cloud Operations Engineer.

---

## 1. Mission

Bangun **Cloud Cost Lab**, sebuah platform FinOps yang membantu engineer memahami:

- ke mana biaya cloud pergi;
- resource mana yang idle atau overprovisioned;
- bagaimana cost berkaitan dengan utilization;
- berapa potential savings;
- bagaimana tren dan forecast biaya;
- apakah budget berisiko terlampaui;
- recommendation optimasi mana yang paling layak dikerjakan terlebih dahulu;
- bagaimana memverifikasi **realized savings** setelah optimasi.

Project harus menunjukkan **engineering judgment**, bukan sekadar dashboard CRUD.

Prinsip utama:

1. Cost visibility
2. Cost allocation
3. Cost optimization
4. Cost forecasting
5. Resource efficiency
6. Reliability awareness
7. Security awareness
8. Automation
9. Evidence-based recommendations
10. Human approval
11. Least privilege
12. Reproducibility
13. Infrastructure as Code
14. Observability
15. Cost-aware engineering

---

## 2. User Context

User adalah mahasiswa semester 4.

Hardware utama:

- MacBook Pro 2020
- Apple Silicon M1
- RAM 8 GB
- SSD 256 GB
- macOS

Cloud utama:

- Google Cloud Platform (GCP)

Target career:

- Cloud Engineer
- DevOps Engineer
- Infrastructure Engineer
- SRE
- Platform Engineer
- Cloud Operations Engineer
- FinOps / Cloud Cost Optimization Engineer

### Resource constraints

Karena MacBook hanya memiliki RAM 8 GB:

- jangan menjalankan terlalu banyak container sekaligus;
- hindari database lokal besar;
- gunakan workload cloud hanya ketika memang diperlukan;
- gunakan Docker Compose secara selektif;
- hindari Kubernetes lokal besar;
- gunakan mock mode untuk demo ketika memungkinkan;
- jangan menjalankan model AI besar secara lokal;
- prioritaskan desain yang ringan dan mudah dipahami.

---

## 3. Project Identity

Nama utama:

**Cloud Cost Lab**

Subtitle:

**GCP FinOps & Cloud Cost Optimization Platform**

Optional codename:

**CloudCostOps**

Gunakan nama secara konsisten pada:

- repository;
- README;
- UI;
- dokumentasi;
- diagram;
- API;
- dashboard;
- Docker image;
- CV/LinkedIn description.

---

## 4. Core Product Statement

> Cloud Cost Lab aggregates cloud cost and resource utilization data, detects waste and optimization opportunities, estimates potential savings, monitors budgets, forecasts future cost, and provides evidence-based recommendations with human approval before impactful actions.

Jangan membuat klaim yang tidak didukung data.

Gunakan istilah:

- estimated;
- potential;
- observed;
- based on available data;
- project-specific heuristic.

Jangan menggunakan:

- guaranteed savings;
- exact forecast tanpa confidence/range;
- realized savings sebelum benar-benar diverifikasi.

---

## 5. Architecture

Target architecture:

```text
                   GCP
                    |
            +-------+-------+
            |               |
            v               v
      Billing Export     Monitoring
            |               |
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

### Architectural goals

- GCP-first;
- small and understandable;
- modular;
- extensible toward multi-cloud;
- safe by default;
- data-driven;
- cost-aware;
- observable;
- testable.

---

## 6. Technology Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend

- Python
- FastAPI
- Pydantic

### Database

- PostgreSQL

### Data / analytics

- SQL
- Python
- Pandas only where it provides clear value

### Cloud

- Google Cloud Platform
- Cloud Billing
- Billing Export
- BigQuery
- Cloud Monitoring
- Cloud Logging
- Compute Engine
- Cloud SQL
- Cloud Storage
- Artifact Registry
- IAM
- Service Accounts
- Secret Manager

Optional only when justified:

- GKE
- Cloud Run
- Pub/Sub
- Cloud Scheduler
- Cloud Functions

### Infrastructure as Code

- Terraform

### CI/CD

- GitHub Actions

### Security

- Trivy
- Gitleaks
- Secret Manager
- IAM
- Workload Identity Federation when feasible

### Observability

- Google Cloud Monitoring
- Google Cloud Logging
- Prometheus when useful for custom application metrics
- Grafana when useful for local/demo visualization

### AI

- pluggable LLM provider;
- read-only by default.

---

## 7. Important GCP Cost Safety Rules

**Cloud Cost Lab itself must not become an expensive cloud project.**

Before creating any GCP resource, determine:

1. Is it billable?
2. What is the purpose?
3. What is the smallest practical configuration?
4. How can it be shut down?
5. How can it be destroyed?
6. What IAM permissions are needed?
7. What is the rollback path?

Before running `terraform apply`, show:

- resources to be created;
- why they are needed;
- potential billing impact;
- rollback/destroy method.

Never silently create expensive infrastructure.

Prefer:

- mock mode;
- small resources;
- limited retention;
- bounded queries;
- scheduled shutdown;
- budget alerts;
- explicit destroy procedures.

---

## 8. Billing Data Strategy

Support two modes.

### Mode A — Real GCP data

Use GCP Billing Export to BigQuery where available.

Configuration should be externalized:

```text
GCP_BILLING_PROJECT
GCP_BILLING_DATASET
GCP_BILLING_TABLE
```

Document:

- how billing export is enabled;
- required permissions;
- expected schema;
- data freshness;
- privacy implications;
- BigQuery query cost implications.

### Mode B — Demo / Mock data

The application **must work without GCP billing access**.

Support:

```text
DEMO_MODE=true
```

In demo mode:

- use synthetic billing data;
- use synthetic utilization data;
- run locally;
- do not require GCP credentials;
- keep the dashboard and recommendation engine functional.

The mock provider and real provider should share an abstraction such as:

```text
BillingDataProvider
├── RealBillingProvider
└── MockBillingProvider
```

---

## 9. BigQuery Cost Protection

If Billing Export uses BigQuery:

- never use `SELECT *` for large billing tables;
- always filter by date/partition where possible;
- select only required columns;
- aggregate early;
- avoid repeated full-table scans;
- use query limits where appropriate;
- use dry-run/bytes-estimate mechanisms when available;
- document expensive vs optimized queries.

Create:

```text
docs/bigquery-cost.md
```

with:

- bad query examples;
- optimized query examples;
- query-cost considerations;
- data retention considerations.

---

## 10. Core Data Model

### CostRecord

Fields:

- project_id
- project_name
- service
- sku
- region
- resource_id when available
- usage_date
- usage_amount
- usage_unit
- cost
- currency
- credits
- net_cost
- environment
- labels
- tags

### ResourceRecord

Fields:

- resource_id
- project_id
- resource_type
- service
- region
- zone
- status
- created_at
- last_seen
- labels
- environment

### UsageRecord

Fields:

- resource_id
- timestamp
- cpu_utilization
- memory_utilization
- disk_utilization
- network_in
- network_out
- request_count
- latency
- error_rate

Not every resource will expose every metric. The model must remain flexible.

---

## 11. Database Model

Use PostgreSQL.

Minimum tables:

```text
projects
services
resources
resource_usage
cost_records
budgets
recommendations
savings
anomalies
forecast_runs
policies
audit_logs
```

Suggested indexes:

- project_id
- service
- usage_date
- resource_id
- environment

Do not retain unlimited raw data without reason.

---

## 12. Cost Dimensions

Dashboard and APIs must be able to group/filter by:

- Project
- Service
- SKU
- Region
- Resource
- Environment
- Team
- Application
- Label
- Date

Support environments:

- development
- staging
- production

Useful labels/tags:

- environment
- team
- application
- owner

If attribution is missing:

**UNALLOCATED**

Never guess ownership.

---

## 13. Application Pages

Create these main frontend routes:

```text
/
/cost
/resources
/recommendations
/savings
/forecast
/budget
/utilization
/policies
/reports
/ai
/settings
```

### Overview

Show:

- current month cost;
- previous month;
- MoM change;
- projected month end;
- potential savings;
- realized savings;
- active recommendations;
- budget status;
- data freshness.

### Cost Explorer

Filters:

- date range;
- service;
- project;
- environment;
- region;
- resource;
- team.

Charts:

- daily cost;
- weekly cost;
- monthly cost;
- service breakdown;
- project breakdown;
- environment breakdown.

### Resource Inventory

Columns:

- resource;
- type;
- project;
- region;
- status;
- utilization;
- monthly cost;
- potential saving;
- risk.

### Recommendations

Show:

- title;
- resource;
- evidence;
- current cost;
- potential cost;
- potential savings;
- savings percentage;
- risk;
- confidence;
- effort;
- priority;
- approval state.

---

## 14. Cost Analysis

Calculate:

- current period cost;
- previous period cost;
- WoW change;
- MoM change;
- average daily cost;
- average monthly cost;
- highest spending day;
- highest spending service;
- top resources;
- unallocated cost.

Detect unexpected growth.

Example:

```text
Cost increased 42% compared with previous week.
```

Explain which service/resource contributed to the increase.

---

## 15. Budget System

Support user-defined budget:

```text
Monthly budget: $50
Warning: 70%
Critical: 90%
Exceeded: 100%
```

Calculate:

- actual spend;
- remaining budget;
- budget utilization;
- projected month-end spend;
- forecast-over-budget risk.

Do not automatically stop production resources.

---

## 16. Idle Resource Detection

Example Compute Engine heuristic:

```text
CPU average < 5%
AND
network activity minimal
AND
stable for >= 7 days
```

Recommendation must show:

- evidence;
- duration;
- current cost;
- estimated saving;
- confidence;
- risk.

Never auto-delete resources merely because they appear idle.

---

## 17. Rightsizing

Create a pluggable rule-based rightsizing engine.

Example:

```text
IF
CPU avg < 20%
AND
memory avg < 40%
AND
workload stable
THEN
recommend smaller instance
```

Recommendation must include:

- current machine type;
- proposed type;
- observed usage;
- estimated cost change;
- potential savings;
- performance risk;
- confidence.

Do not blindly downsize production.

---

## 18. Storage Optimization

Detect when possible:

- unattached disks;
- stale snapshots;
- unused storage;
- unnecessary retention;
- oversized volumes where evidence exists.

Possible actions:

- delete;
- archive;
- resize;
- change retention.

Always communicate recovery risk.

---

## 19. Database Optimization

For Cloud SQL, use available metrics such as:

- CPU;
- memory;
- connections;
- storage;
- query behavior if available.

Detect underutilization and produce cautious recommendations.

Never claim a size change is safe without evidence.

---

## 20. Artifact Registry Optimization

Where supported, identify:

- stale image versions;
- excessive retention;
- large images;
- unnecessary artifacts.

Recommend retention policies.

Never delete production artifacts automatically.

---

## 21. GKE / Cloud Run Optimization

These are optional advanced modules.

### GKE

Analyze where data is available:

- node cost;
- utilization;
- pod requests;
- oversized requests;
- idle workloads;
- autoscaling opportunities.

### Cloud Run

Analyze:

- requests;
- CPU;
- memory;
- execution duration;
- instance count;
- min/max instances;
- concurrency.

Only implement when it adds meaningful learning value.

---

## 22. Recommendation Engine

Create a pluggable recommendation architecture.

Suggested rules:

```text
IdleComputeRule
OversizedComputeRule
UnusedDiskRule
StorageRetentionRule
ArtifactRetentionRule
CloudSQLRightsizingRule
GKEOptimizationRule
BudgetRiskRule
CostAnomalyRule
```

Each rule should expose behavior equivalent to:

```text
evaluate()
explain()
calculate_saving()
calculate_risk()
confidence()
```

Every recommendation must answer:

1. What is wrong?
2. What evidence supports it?
3. How much could be saved?
4. What is the risk?
5. How much effort is required?
6. Who must approve it?
7. What should happen next?

---

## 23. Recommendation Lifecycle

Use:

```text
OPEN
APPROVED
REJECTED
IMPLEMENTED
VERIFIED
```

Workflow:

```text
Detect
→ Recommend
→ Approve
→ Implement
→ Measure
→ Verify
```

Never call something **realized savings** until actual post-change data has been observed.

---

## 24. Priority / ROI Model

Prioritize based on:

- potential savings;
- confidence;
- risk;
- engineering effort.

Example:

```text
HIGH PRIORITY
Savings: $15/month
Risk: LOW
Confidence: HIGH
Effort: LOW
```

Avoid pretending the score is an industry standard.

Call it:

**project-specific optimization priority score**.

---

## 25. Cost Optimization Score

Create a project-specific heuristic score based on:

- idle resources;
- rightsizing opportunities;
- tag/label coverage;
- budget compliance;
- storage hygiene;
- utilization efficiency;
- automation coverage.

Clearly label it as a project-specific heuristic.

---

## 26. FinOps Health Score

Dimensions:

- Visibility
- Allocation
- Optimization
- Governance
- Forecasting
- Automation

Example UI:

```text
Visibility:     90
Allocation:    72
Optimization:  68
Governance:    65
Forecasting:   74
Automation:    40

FinOps Health: 68/100
```

Clearly label as heuristic.

---

## 27. Forecasting

Start simple.

Preferred first implementations:

- moving average;
- linear regression.

Optional later:

- more advanced time-series methods.

Forecast:

- 30-day;
- optional 90-day.

Always show a range or confidence indicator.

Example:

```text
Expected: $48.20
Range:    $44 - $53
```

Never present uncertain forecasts as exact values.

---

## 28. Cost Anomaly Detection

Phase 1:

- rolling average;
- threshold comparison.

Phase 2:

- z-score.

Optional Phase 3:

- Isolation Forest.

Example:

```text
Normal daily cost: $1.40
Observed:          $5.90
Increase:          +321%
```

Alert must identify:

- project;
- service;
- resource if possible;
- start time;
- estimated impact.

---

## 29. Unit Economics

If application metrics are available, calculate:

- cost per request;
- cost per transaction;
- cost per user;
- cost per API call.

Example:

```text
Monthly infrastructure: $100
Requests:               2,000,000
Cost/request:           $0.00005
```

This is a business-aware FinOps feature.

---

## 30. Cost Simulator

Implement a What-if simulator.

Example:

```text
Current:
e2-standard-4

Proposed:
e2-standard-2

Current cost:       $40/month
Estimated new cost: $27/month
Potential saving:   $13/month

Performance risk:   MEDIUM
```

Clearly label simulation values as:

**SIMULATION — NOT REALIZED SAVINGS**

---

## 31. Scheduling Optimization

For development resources only, support recommendations such as:

```text
08:00 → ON
18:00 → OFF
Weekend → OFF
```

Estimate:

- hours saved;
- monthly savings;
- annualized savings.

Do not apply to production by default.

---

## 32. Cost Guardrails / Policies

Support policies such as:

```text
MAX_MONTHLY_COST
MAX_DEV_INSTANCES
NO_PUBLIC_DATABASE
REQUIRE_COST_LABELS
REQUIRE_OWNER_LABEL
MAX_IDLE_DAYS
```

Policy result:

- PASS
- WARNING
- VIOLATION

---

## 33. AI Cloud Cost Advisor

Add an optional AI module.

Name:

**AI Cloud Cost Advisor**

It should answer questions such as:

- Where can I save the most money?
- Why did cost increase this week?
- Which VM should I resize?
- Which resources are idle?
- What is my budget risk?
- What should I optimize first?

Provide structured context to the model.

Typical output:

```text
Summary
Evidence
Likely Cause
Recommendation
Potential Savings
Risk
Confidence
```

---

## 34. AI Safety Model

AI is **READ-ONLY by default**.

AI may:

- analyze;
- summarize;
- explain;
- prioritize;
- recommend.

AI must not directly:

- delete production resources;
- modify IAM;
- change firewall rules;
- destroy Terraform infrastructure;
- delete databases;
- disable monitoring;
- make destructive production changes.

Action workflow:

```text
AI analysis
↓
Recommendation
↓
Human approval
↓
Validated action
↓
Audit log
```

---

## 35. Example AI Root-Cause Analysis

Question:

> Why did cloud cost increase 35% this week?

AI should inspect:

- service spend;
- resource changes;
- utilization changes;
- deployment events;
- anomalies.

Example output:

```text
Summary
Compute Engine cost increased 62%.

Evidence
- previous VM count: 4
- current VM count: 7
- average dev CPU: 11%

Estimated impact
$14/month excess cost

Recommendation
Review new development VMs and enforce a schedule policy.

Confidence
High
```

---

## 36. Security

Implement:

- least-privilege IAM;
- Secret Manager;
- no service account keys committed to Git;
- no credentials in source code;
- environment variables;
- GitHub secrets;
- Workload Identity Federation when feasible;
- Trivy;
- Gitleaks.

Separate read-only and optional automation identities.

---

## 37. GCP IAM Model

Prefer separate service accounts where practical.

Example:

```text
cost-data-reader
monitoring-reader
cost-optimizer
```

The `cost-optimizer` account must **not** receive broad `Owner` or `Editor` permissions merely for convenience.

Use the smallest set of roles necessary.

---

## 38. Automation Safety

Support four modes:

### Mode 1 — Observation

Only inspect resources.

### Mode 2 — Recommendation

Generate recommendations.

### Mode 3 — Human Approval

Require approval.

### Mode 4 — Controlled Automation

Only for explicitly safe, bounded actions.

Default to **Mode 1/2**.

Safe examples may include:

- generate report;
- label resource;
- schedule a development VM;
- send notification.

Do not default to:

- delete production;
- modify production DB;
- change IAM;
- destroy network;
- destroy Terraform state.

---

## 39. API

Use FastAPI.

Minimum endpoints:

```text
GET /health
GET /ready

GET /api/cost
GET /api/cost/trend
GET /api/cost/by-service
GET /api/cost/by-project
GET /api/cost/by-environment

GET /api/resources
GET /api/resources/{id}

GET /api/utilization
GET /api/recommendations
GET /api/recommendations/{id}

GET /api/savings
GET /api/forecast
GET /api/budget
GET /api/anomalies
GET /api/finops-score

POST /api/recommendations/{id}/approve
POST /api/recommendations/{id}/reject
```

Use:

- Pydantic;
- pagination;
- filtering;
- validation;
- structured errors;
- request IDs;
- bounded queries.

Do not expose unbounded datasets.

---

## 40. Observability

Application metrics should include where useful:

```text
http_requests_total
http_request_duration_seconds
cost_records_processed_total
recommendations_generated_total
forecast_runs_total
billing_query_duration_seconds
```

Logs should use structured JSON:

```json
{
  "timestamp": "2026-08-26T07:00:00Z",
  "level": "INFO",
  "service": "cost-analyzer",
  "operation": "forecast",
  "duration_ms": 230
}
```

Monitor:

- API availability;
- API latency;
- error rate;
- billing query failures;
- stale data;
- pipeline failures;
- recommendation failures;
- forecast failures;
- cost anomalies.

---

## 41. Data Freshness

Cost data must show freshness.

Example:

```text
Last update:
2026-08-26 04:00 UTC

Age:
3 hours

Status:
FRESH
```

If data is older than the configured threshold:

```text
STALE
```

Never present stale billing data as current.

---

## 42. Data Quality

Track:

- missing labels;
- missing resource IDs;
- duplicate records;
- malformed records;
- stale records.

Create a **Data Quality Score** as a project-specific heuristic.

Example:

```text
94 / 100
```

---

## 43. SRE Layer

Although this is a FinOps project, apply SRE thinking.

SLIs:

- API availability;
- cost-data freshness;
- recommendation pipeline success.

Example SLOs:

```text
API availability >= 99.5%
Cost data freshness < 24h
Recommendation pipeline success >= 99%
```

Track:

- MTTD;
- MTTR.

---

## 44. Incident Scenarios

Create at least these scenarios:

### INC-001
Unexpected Compute cost spike

### INC-002
Billing data stale

### INC-003
BigQuery query failure

### INC-004
Recommendation engine failure

### INC-005
Forecast exceeds budget

Each incident document must include:

- severity;
- detection;
- impact;
- timeline;
- root cause;
- resolution;
- MTTD;
- MTTR;
- prevention.

---

## 45. Reports

Generate:

- daily report;
- weekly report;
- monthly report.

Report sections:

1. Executive Summary
2. Cost Trend
3. Top Services
4. Top Resources
5. Cost Anomalies
6. Optimization Opportunities
7. Potential Savings
8. Realized Savings
9. Budget Status
10. Forecast
11. Risks
12. Recommended Actions

Possible formats:

- Markdown
- HTML
- PDF as optional extension

---

## 46. Repository Structure

Target structure:

```text
cloud-cost-lab/
├── apps/
│   ├── api/
│   └── web/
│
├── data/
│   └── mock/
│
├── analytics/
│   ├── cost/
│   ├── utilization/
│   ├── recommendations/
│   └── forecasting/
│
├── terraform/
│   ├── modules/
│   └── environments/
│
├── monitoring/
│
├── scripts/
│
├── docs/
│   ├── architecture.md
│   ├── finops.md
│   ├── rightsizing.md
│   ├── forecasting.md
│   ├── security.md
│   ├── cost-safety.md
│   ├── runbook.md
│   ├── interview-preparation.md
│   ├── cv-description.md
│   ├── decisions/
│   ├── reports/
│   └── incidents/
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── CLAUDE.md
```

---

## 47. Documentation Requirements

README must contain:

1. Project Overview
2. Problem
3. Why FinOps
4. Architecture
5. GCP Services
6. Data Model
7. Cost Model
8. Recommendation Engine
9. Forecasting
10. Budgeting
11. Cost Optimization
12. Security
13. Terraform
14. Deployment
15. AI Advisor
16. Demo
17. Testing
18. Cost Considerations
19. Limitations
20. Future Work

Required documentation files:

```text
docs/
├── architecture.md
├── gcp-setup.md
├── billing-export.md
├── bigquery-cost.md
├── cost-model.md
├── resource-analysis.md
├── rightsizing.md
├── budget.md
├── anomaly-detection.md
├── forecasting.md
├── recommendation-engine.md
├── savings.md
├── finops.md
├── security.md
├── terraform.md
├── observability.md
├── ai-advisor.md
├── troubleshooting.md
├── runbook.md
├── demo-scenarios.md
├── cost-safety.md
├── interview-preparation.md
├── cv-description.md
├── reports/
├── incidents/
└── decisions/
```

---

## 48. Architecture Decision Records

Create ADRs such as:

```text
docs/decisions/
├── ADR-001-why-gcp.md
├── ADR-002-why-fastapi.md
├── ADR-003-why-postgresql.md
├── ADR-004-why-bigquery.md
├── ADR-005-why-terraform.md
├── ADR-006-why-nextjs.md
├── ADR-007-why-mock-mode.md
└── ADR-008-why-ai-read-only.md
```

Each ADR must contain:

- Context
- Decision
- Alternatives
- Trade-offs
- Consequences

---

## 49. Local Development

Local default stack:

```text
backend
frontend
postgresql
```

Use Docker Compose.

Do not require local GCP or BigQuery for standard demo mode.

Recommended startup flow:

```text
cp .env.example .env

docker compose up -d
```

Exact commands should be validated against the actual repository.

---

## 50. Docker Rules

Images should:

- be small;
- use pinned versions;
- use non-root user when practical;
- not contain secrets;
- include healthchecks where useful;
- avoid `latest` for deployment references;
- support `linux/arm64` and `linux/amd64` where feasible.

---

## 51. Terraform Rules

Terraform structure:

```text
terraform/
├── modules/
│   ├── billing/
│   ├── bigquery/
│   ├── service-account/
│   ├── storage/
│   └── compute/
├── environments/
│   ├── dev/
│   └── demo/
├── provider.tf
├── variables.tf
└── outputs.tf
```

Required validation:

```text
terraform fmt -check
terraform validate
terraform plan
```

Use `terraform apply` only after the plan has been reviewed.

Always document `terraform destroy`.

---

## 52. CI/CD

GitHub Actions pipeline:

1. lint;
2. test;
3. build;
4. security scan;
5. Docker build;
6. image scan;
7. publish image;
8. optional deployment.

Use:

- Trivy;
- Gitleaks;
- GitHub Secrets;
- Workload Identity Federation where feasible.

Avoid static GCP credentials when a federated identity is practical.

---

## 53. Git Workflow

Branches:

```text
main
develop
feature/*
fix/*
infra/*
docs/*
```

Use Conventional Commits:

```text
feat:
fix:
docs:
refactor:
test:
infra:
security:
perf:
```

Examples:

```text
feat(cost): add monthly cost aggregation
feat(finops): add idle resource detection
feat(forecast): add 30-day projection
infra(gcp): add billing dataset
security(iam): reduce billing reader permissions
```

---

## 54. Testing

### Backend

- pytest
- unit tests
- integration tests

### Frontend

- unit tests;
- optional Playwright end-to-end tests.

### Infrastructure

```text
terraform fmt -check
terraform validate
terraform plan
```

### Security

- Trivy
- Gitleaks

### Business logic tests

Must validate:

- cost aggregation;
- credits;
- net cost;
- MoM;
- WoW;
- budget percentage;
- forecast;
- saving percentage;
- realized savings;
- unallocated cost.

---

## 55. Demo Dataset

Create realistic mock data:

```text
data/mock/projects.json
data/mock/resources.json
data/mock/cost.json
data/mock/usage.json
data/mock/recommendations.json
data/mock/forecast.json
```

Example cost progression:

```text
Month 1: $42
Month 2: $48
Month 3: $61
```

Simulate:

- Compute +35%;
- Cloud SQL +10%;
- one idle VM;
- one oversized VM;
- one unallocated resource;
- one budget-risk period.

---

## 56. Required Demo Scenarios

### Scenario 1 — Idle VM

Detect low utilization and recommend schedule/rightsizing.

### Scenario 2 — Oversized VM

Compare current machine type with a smaller candidate.

### Scenario 3 — Unexpected Cost Spike

Detect a sudden increase and explain the source.

### Scenario 4 — Budget Risk

Show current spend vs forecast and budget.

### Scenario 5 — Unused Disk

Detect and estimate savings.

### Scenario 6 — Development Scheduling

Simulate off-hours shutdown and calculate potential savings.

### Scenario 7 — Cloud SQL Underutilization

Provide cautious rightsizing recommendation.

### Scenario 8 — Unallocated Cost

Highlight missing labels/tags.

---

## 57. Portfolio / Personal Brand Requirements

This project is a portfolio flagship, not just an internal exercise.

README should make these skills immediately visible:

- GCP
- FinOps
- Cloud Cost Optimization
- Infrastructure Engineering
- Terraform
- Observability
- Security
- Data Analysis
- SRE thinking
- AI-assisted engineering

Include:

- architecture diagram;
- screenshots;
- short demo video/GIF if possible;
- measurable examples;
- design decisions;
- limitations;
- lessons learned.

---

## 58. Portfolio Demo Script

Prepare a 5-minute demo:

1. Open Overview.
2. Show monthly cost.
3. Show trend.
4. Show top services.
5. Open resource inventory.
6. Show idle VM.
7. Open recommendation.
8. Show evidence and potential savings.
9. Open budget.
10. Show forecast.
11. Ask AI: `Where can I save money?`
12. Show recommendation.
13. Show human approval workflow.
14. Show audit log.

The demo should tell a coherent engineering story.

---

## 59. Interview Preparation

Create `docs/interview-preparation.md` with implementation-based answers for:

1. What problem does this solve?
2. Why FinOps?
3. Why GCP?
4. Why BigQuery?
5. How is billing data collected?
6. How do you avoid expensive BigQuery queries?
7. How do you detect idle resources?
8. What is rightsizing?
9. How do you calculate potential savings?
10. How do you distinguish potential vs realized savings?
11. How do you forecast?
12. How do you detect anomalies?
13. How do you secure GCP credentials?
14. Why Terraform?
15. Why use mock mode?
16. How do you handle stale billing data?
17. How do you handle missing labels?
18. How would you scale to 100 GCP projects?
19. How would you support AWS/Azure later?
20. How does AI help?
21. Why is AI read-only?
22. How would you prevent unsafe automation?
23. What are the trade-offs of your architecture?
24. What would you change in a real production system?

Answers must match actual implementation.

---

## 60. CV Description

Create `docs/cv-description.md` with:

- one-line version;
- three-line version;
- CV bullet points;
- LinkedIn version;
- GitHub description;
- interview explanation.

Do not exaggerate.

---

## 61. Project Phases

Do not build everything at once.

### PHASE 0 — Planning

Architecture, decisions, repository structure, definition of done.

### PHASE 1 — Local Mock Platform

FastAPI + PostgreSQL + demo data.

### PHASE 2 — Cost Explorer

Aggregation, charts, filters.

### PHASE 3 — Resource Inventory

Resources, usage, cost linkage.

### PHASE 4 — Recommendation Engine

Idle, rightsizing, storage.

### PHASE 5 — Budget

Budget and alerts.

### PHASE 6 — Forecasting

30-day forecast.

### PHASE 7 — Anomaly Detection

Cost spikes and anomalies.

### PHASE 8 — Savings Tracking

Potential vs realized savings.

### PHASE 9 — GCP Integration

Billing Export + BigQuery.

### PHASE 10 — Monitoring / Data Freshness

GCP Monitoring/Logging as appropriate.

### PHASE 11 — Terraform

Infrastructure as Code.

### PHASE 12 — Security

IAM, secrets, scanning.

### PHASE 13 — CI/CD

GitHub Actions.

### PHASE 14 — FinOps Score

Visibility, allocation, optimization, governance, forecast, automation.

### PHASE 15 — Reports

Daily/weekly/monthly report generation.

### PHASE 16 — AI Advisor

Read-only contextual assistant.

### PHASE 17 — Demo Scenarios

Synthetic incident/cost scenarios.

### PHASE 18 — Portfolio Preparation

README, screenshots, demo, CV, interview prep.

---

## 62. Implementation Method

Do **not** generate the entire project in one response.

For every phase:

1. inspect repository;
2. explain the current state;
3. explain objective;
4. explain architecture impact;
5. list files to create/change;
6. implement small increments;
7. run validation;
8. fix failures;
9. update docs;
10. provide phase status.

Do not automatically start the next phase.

---

## 63. Repository Awareness

When working in Claude Code:

Before modifying anything:

1. inspect the repository;
2. read relevant existing files;
3. identify the current architecture;
4. reuse existing components when appropriate;
5. avoid overwriting unrelated work;
6. preserve working functionality.

Never blindly regenerate the entire repository.

---

## 64. Coding Rules

When writing code:

- prefer small functions;
- use clear names;
- use type hints in Python;
- use strict TypeScript;
- validate external data;
- handle errors explicitly;
- use environment variables;
- provide `.env.example`;
- never hardcode credentials;
- do not use `latest` in deploy references;
- pin important dependencies;
- avoid unnecessary abstractions;
- document trade-offs;
- consider ARM64 compatibility;
- consider GCP cost;
- add tests for business logic.

If an existing bug is found, fix the root cause.

---

## 65. Major Technology Decision Rule

For every major technology, answer:

```text
WHAT?
WHY?
ALTERNATIVE?
TRADE-OFF?
FAILURE MODE?
SECURITY?
COST?
```

Do not introduce technology simply because it is popular.

If a technology adds complexity without clear value, prefer a simpler solution.

---

## 66. Definition of Done

A feature is not complete merely because the code compiles.

A feature is complete only when:

- [ ] code exists;
- [ ] tests exist;
- [ ] validation passes;
- [ ] documentation exists;
- [ ] error handling exists;
- [ ] security implications are reviewed;
- [ ] cost implications are considered;
- [ ] failure mode is considered;
- [ ] UI/API behavior is verified when applicable;
- [ ] observability is added when appropriate.

---

## 67. Phase Status Format

At the end of every phase print:

```text
-----------------------------------------------
PHASE STATUS
-----------------------------------------------

Phase:

Completed:
...

Validation:
...

Tests:
...

Security:
...

Cost Risk:
...

Known Issues:
...

Next Phase:
...

-----------------------------------------------
```

Do not automatically begin the next phase.

---

## 68. Final Success Criteria

The final project should be able to demonstrate:

- [ ] Mock mode
- [ ] Real GCP billing integration
- [ ] Cost Explorer
- [ ] Resource inventory
- [ ] Utilization analysis
- [ ] Idle detection
- [ ] Rightsizing
- [ ] Storage optimization
- [ ] Budget
- [ ] Forecast
- [ ] Cost anomaly detection
- [ ] Potential savings
- [ ] Realized savings
- [ ] FinOps score
- [ ] Policy engine
- [ ] Cost reports
- [ ] BigQuery query cost protection
- [ ] Terraform
- [ ] IAM least privilege
- [ ] Security scans
- [ ] Observability
- [ ] AI Advisor
- [ ] Audit log
- [ ] Incident documentation
- [ ] Interview preparation
- [ ] CV-ready description
- [ ] Portfolio-ready README

---

## 69. Final Portfolio Story

The final project should allow the user to explain:

> “I built a GCP FinOps platform to understand how cloud infrastructure cost relates to resource utilization. The platform aggregates billing and usage data, identifies idle and oversized resources, estimates potential savings, monitors budgets, forecasts future costs, and produces evidence-based optimization recommendations. I designed the system so recommendations require human approval before impactful actions are taken. I also added security, observability, Terraform, CI/CD, audit logging, and an optional AI advisor.”

That statement must remain truthful to what is actually implemented.

---

## 70. FIRST TASK FOR CLAUDE CODE

Start with **PHASE 0 ONLY**.

Do not implement the full application yet.

First:

1. inspect the repository;
2. summarize the current repository state;
3. produce the proposed architecture;
4. produce technology decisions;
5. produce repository structure;
6. produce the phase roadmap;
7. define cost safety strategy;
8. define security strategy;
9. define FinOps model;
10. define data model;
11. define Definition of Done;
12. create initial ADRs if appropriate.

Then stop.

Do not start PHASE 1 until explicitly instructed.

---

# End of CLAUDE.md
