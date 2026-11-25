# CV Description — Cloud Cost Lab

## One-Line

Built a GCP FinOps platform that correlates billing data with resource utilization to detect waste and generate evidence-based optimization recommendations.

## Three-Line

Built a GCP FinOps platform that aggregates billing and utilization data, detects idle and oversized resources, and generates evidence-based cost optimization recommendations. Implemented 30-day forecasting, anomaly detection (z-score), budget monitoring, and an AI advisor with read-only safety constraints. Designed with SRE practices (SLI/SLO), CI/CD security scanning (Trivy/Gitleaks), and Terraform infrastructure.

## CV Bullet Points

### Cloud Engineer / DevOps Role

- Designed and built a GCP FinOps platform that identifies cloud waste through cost-utilization correlation, detecting idle resources (CPU <5%) and generating prioritized optimization recommendations
- Implemented GCP Billing Export integration (BigQuery) with partition-aware queries, achieving <$0.10/month query cost through cost-safe patterns
- Created Terraform modules (IAM, BigQuery, Storage, Compute) with least-privilege service accounts and documented destroy procedures
- Built CI/CD pipeline with GitHub Actions: automated testing (329 tests), security scanning (Trivy + Gitleaks), and multi-arch Docker builds (amd64 + arm64)
- Implemented SRE practices: SLI/SLO monitoring (99.5% availability target), incident response procedures, and operational runbooks

### Infrastructure Engineer / SRE Role

- Built an observability system with application metrics, SLI/SLO tracking, threshold-based alerting, and structured JSON logging
- Designed provider abstractions (BillingDataProvider, MonitoringDataProvider) enabling seamless switching between mock and real GCP data
- Implemented budget monitoring with four severity levels (HEALTHY/WARNING/CRITICAL/EXCEEDED) and projected breach detection
- Created 5 incident response procedures with MTTD/MTTR targets and corresponding operational runbooks
- Enforced security: least-privilege IAM, Workload Identity Federation documentation, sensitive data filtering, no credentials in code

### FinOps / Cloud Cost Optimization Role

- Built recommendation engine with 5 rules (idle compute, oversized, unused disk, storage retention, cost anomaly) producing evidence-based savings estimates
- Implemented savings verification workflow (OPEN → APPROVED → IMPLEMENTED → VERIFIED) distinguishing potential from realized savings
- Created 30-day cost forecasting (hybrid: linear trend + moving average) with confidence ranges
- Developed anomaly detection using z-score analysis with attribution (identifies which service/resource caused the spike)
- Designed governance policies (5 rules) enforcing cost controls without automatic destructive actions

## GitHub Description

GCP FinOps platform — cost visibility, utilization analysis, recommendations, forecasting, anomaly detection, AI advisor. Built with FastAPI, Next.js, Terraform, GitHub Actions. 329 tests, demo mode.
