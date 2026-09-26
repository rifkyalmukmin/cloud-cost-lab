# CV Description — Cloud Cost Lab

## One-line version

> Built a GCP FinOps platform (FastAPI, Next.js, PostgreSQL, Terraform, GitHub Actions) that links cloud cost to utilization, recommends optimizations with measured evidence, verifies realized savings from actual before/after data, and enforces human approval before any change.

## Three-line version

> Designed and built an end-to-end FinOps platform: FastAPI/PostgreSQL analytics engine joining billing, utilization and performance data; rule-based optimization engine (idle, oversized, anomalies) with priority scoring and evidence-backed recommendations; Next.js dashboard covering cost, utilization, savings verification, budgets and forecasts.
> Operated it like production: 198 backend tests with strict mypy, GitHub Actions CI with Gitleaks/Trivy security gates, multi-arch non-root Docker images, Prometheus metrics with SLIs/SLOs, incident runbooks, and Terraform IaC (plan-reviewed, never auto-applied).
> Enforced responsible FinOps: potential savings are never called realized — realized savings are measured from actual before/after cost data, and every lifecycle decision is recorded in an append-only audit log.

## CV bullet points (pick 3–5)

- Built a full-stack GCP FinOps platform (FastAPI, PostgreSQL, Next.js, Terraform, GitHub Actions) connecting cloud cost with resource utilization and performance data across 15 delivered phases.
- Implemented a rule-based recommendation engine (idle, oversized, storage, cost-anomaly detection) with evidence-gated firing — CPU/traffic/connections guards prevent false positives — and a priority model ranking savings, confidence, risk and effort.
- Designed a savings verification workflow distinguishing potential from realized savings: before/after cost windows measured from actual data, 409-refusal when evidence is missing, and an append-only audit log for every approval decision.
- Achieved production-grade engineering discipline: 198 tests, strict static typing (mypy/tsc), GitHub Actions pipeline with Gitleaks and Trivy gates, multi-arch non-root Docker images, Prometheus metrics with SLI/SLO alerting and incident runbooks.
- Wrote cost-guarded BigQuery analytics (partition-aware, column-pruned, dry-run verified) and Terraform modules with plan-review and destroy-safety defaults; never created unreviewed billable infrastructure.

## Skills evidenced

GCP (BigQuery, Cloud Monitoring, IAM) · FinOps principles · Python/FastAPI · SQL/PostgreSQL · TypeScript/Next.js · Testing (pytest, vitest) · Terraform · GitHub Actions · Docker · Observability (Prometheus, SLI/SLO) · Security scanning (Gitleaks, Trivy) · Technical writing (20+ docs, ADRs, runbooks, incident reports)

## Interview framing (30 seconds)

*"I built a FinOps platform because I wanted to learn how engineering decisions connect to money. It ingests billing and monitoring data through a provider abstraction, detects optimization opportunities with measured evidence — idle VMs, oversized instances, cost anomalies — and pushes them through a human approval lifecycle. The part I'm most careful about: it never calls an estimate 'realized'. Realized savings only exist after verification against actual before/after cost data, and everything is audited. I ran it like production: tests, static typing, security scanning in CI, metrics, SLOs and incident runbooks."*
