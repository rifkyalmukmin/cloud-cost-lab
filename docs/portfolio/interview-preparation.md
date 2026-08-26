# Interview Preparation — Cloud Cost Lab

Answers based on actual implementation. Do not claim features that are not implemented.

---

## 1. What problem does this solve?

Cloud infrastructure costs grow unpredictably because engineers provision resources without continuous monitoring of utilization or efficiency. This platform provides visibility into where money goes, detects waste (idle VMs, oversized instances, unattached disks), and generates evidence-based optimization recommendations with human approval gates.

## 2. Why FinOps?

FinOps is the operational practice of managing cloud costs. It bridges engineering and finance — engineers need to understand cost implications of their infrastructure decisions. This project demonstrates that understanding by building the tooling that enables it.

## 3. Why GCP?

GCP has a mature Billing Export to BigQuery feature that provides rich, queryable billing data. The Monitoring API gives real-time utilization metrics. Terraform's GCP provider is stable. Together, they enable a complete cost-to-utilization correlation pipeline.

## 4. Why BigQuery for billing data?

GCP Billing Export natively exports to BigQuery. BigQuery provides SQL-based analysis of potentially large billing datasets. With partition filtering, queries cost under $0.01. The alternative (Cloud Billing API) has limited historical data and pagination overhead.

## 5. How is billing data collected?

GCP Billing Export writes daily billing records to a BigQuery table (partitioned by date). My `GCPBillingProvider` queries this table with partition-filtered, column-specific queries. In demo mode, `MockBillingProvider` generates deterministic synthetic data instead.

## 6. How do you avoid expensive BigQuery queries?

All queries use `_PARTITIONDATE` filter (mandatory in my code), select specific columns (never `SELECT *`), bound date ranges (max 90 days enforced), and use parameterized queries. I documented good vs bad query patterns in `docs/bigquery-cost.md`. Expected monthly query cost: $0.01-$0.10.

## 7. How do you detect idle resources?

`IdleComputeRule` triggers when CPU average < 5% over 30 days. It checks that the resource is a compute instance (not storage), the metric is not null, and the observation period is sufficient. It does NOT trigger on storage resources or when metrics are unavailable.

## 8. What is rightsizing?

`OversizedComputeRule` detects instances where CPU < 20% AND memory < 40% simultaneously over 30 days. This indicates the instance is larger than needed. It recommends downsizing (e.g., e2-standard-4 → e2-standard-2) with a 40% estimated savings.

## 9. How do you calculate potential savings?

Each rule has a `calculate_saving()` method based on observed utilization:
- Idle: 90% of monthly cost (resource is barely used)
- Oversized: 40% (typical downsize ratio)
- Unused disk: 100% (unattached) or 50% (underutilized)
- Storage retention: 30% (lifecycle policy impact)
- Anomaly: $0 (detective rule, not optimization)

These are estimates. They become "realized savings" only after implementation AND verification with actual billing data.

## 10. How do you distinguish potential vs realized savings?

Lifecycle: OPEN → APPROVED → IMPLEMENTED → VERIFIED. Only VERIFIED recommendations count as "realized savings" — where we have actual before/after cost data. I never call an estimate "realized savings." The formula is: `realized_savings = cost_before - cost_after` (measured from billing data).

## 11. How do you forecast costs?

Hybrid method: 70% linear regression + 30% moving average (14-day window). Forecasts include confidence ranges (±1.5 std dev) and are never presented as exact values. The system explicitly says "Insufficient evidence" when historical data is < 7 days.

## 12. How do you detect anomalies?

Z-score analysis with a 14-day rolling window baseline. When a day's cost exceeds the baseline by > 2.0 standard deviations, it's flagged as an anomaly. Severity: MEDIUM (z-score 2.0-3.0), HIGH (> 3.0). Each anomaly includes attribution: which service and resource caused the spike.

## 13. How do you secure GCP credentials?

No credentials in code. Service account keys are gitignored. Environment variables for all sensitive config. Workload Identity Federation documented as preferred for production (no key files needed). CI/CD uses Gitleaks to scan for accidentally committed secrets.

## 14. Why Terraform?

Terraform is the industry standard for GCP infrastructure management. My modules enforce least-privilege (only bigquery.dataViewer + jobUser for the cost reader). Everything has documented destroy procedures. No `terraform apply` is run without explicit plan review.

## 15. Why use mock mode?

Demo mode enables development, testing, and portfolio demonstration without GCP credentials or billing costs. The same application code runs in both modes — only the provider implementation differs (MockBillingProvider vs GCPBillingProvider).

## 16. How do you handle stale billing data?

Data freshness tracking: FRESH (<36h), STALE (≥36h), UNKNOWN. The dashboard displays freshness status. Alerts fire at 36h (WARNING) and 48h (CRITICAL). The system never presents stale data as current without indication.

## 17. How do you handle missing labels?

Resources without owner/team labels display "UNALLOCATED." The governance policy `REQUIRE_OWNER_LABEL` flags this as a VIOLATION. We never guess ownership — we surface the gap for humans to fix.

## 18. How would you scale to 100 GCP projects?

The provider abstraction supports multi-project. BigQuery can query across projects with cross-project IAM. The recommendation engine processes resources in a loop — it's O(resources × rules). For 100 projects I'd add: caching layer, scheduled data collection (not on-demand), and project-level summaries.

## 19. How would you support AWS/Azure?

Add new providers: `AWSBillingProvider` (Cost Explorer API), `AzureBillingProvider` (Cost Management API). The `BillingDataProvider` interface defines a contract — any cloud that produces cost records in the standard schema works. The recommendation rules are cloud-agnostic (they operate on CPU/memory/cost, not GCP-specific APIs).

## 20. How does AI help?

The AI advisor answers natural language questions about costs ("Why did cost increase?", "Where can I save?"). It receives structured context from all services and produces evidence-based responses. It's useful for prioritizing actions and explaining anomalies in plain language.

## 21. Why is AI read-only?

Allowing AI to modify infrastructure creates unacceptable risk: an LLM could misinterpret context and delete production resources. The workflow is: AI recommends → human reviews → human approves → human (or validated automation) acts. Separation of analysis from action is the core safety principle.

## 22. How would you prevent unsafe automation?

Four modes: Observation (inspect only), Recommendation (generate suggestions), Human Approval (require explicit sign-off), Controlled Automation (only for bounded, safe actions like labeling). The default is Mode 2. Mode 4 is only for explicitly safe operations like adding labels or sending notifications.

## 23. What are the trade-offs of your architecture?

- **Monorepo**: simpler for one engineer, but harder to deploy independently
- **Python backend + TypeScript frontend**: two languages, but each optimal for its domain
- **In-memory analytics**: fast for demo, but doesn't persist across restarts
- **Rule-based AI**: works without LLM, but less flexible than real NLP
- **Mock mode**: zero-cost development, but data doesn't reflect real-world patterns exactly

## 24. What would you change in a real production system?

- PostgreSQL for persistent state (not in-memory)
- Redis for caching expensive queries
- Pub/Sub for real-time cost event processing
- Separate data collection service (scheduled, not on-demand)
- GKE or Cloud Run for deployment (not Docker Compose)
- Proper authentication (OAuth2 / Identity-Aware Proxy)
- Horizontal scaling for the API layer
- Data retention policies with automated cleanup
- Prometheus + Grafana for production monitoring (not in-memory metrics)
