# LinkedIn Description — Cloud Cost Lab

## Short post version

> I built a GCP FinOps platform to answer a question consoles don't: not just *where does the money go*, but *what is the evidence, and did the saving actually happen?*
>
> **Cloud Cost Lab** joins billing data with resource utilization and performance, detects idle/oversized/cost-anomaly findings with measured evidence, and pushes every recommendation through a human approval lifecycle. The part I'm proudest of: savings are never called "realized" until they're verified against actual before/after cost data — and if costs went up after a change, the platform stores that negative number as measured.
>
> Built with FastAPI + PostgreSQL + Next.js + Terraform, run like production: 190+ tests, strict typing, Gitleaks/Trivy security gates, multi-arch Docker, Prometheus metrics with SLI/SLO alerting and incident runbooks. Runs entirely on deterministic demo data — zero cloud credentials needed.

## Longer post version (with lessons)

> **Why I built a FinOps platform instead of another CRUD app**
>
> Cloud bills are opaque: consoles show costs, but they don't join them to utilization, don't quantify uncertainty, and don't enforce a human approval loop. So I built **Cloud Cost Lab** — a full-stack GCP FinOps platform covering the complete optimization loop:
>
> 🔍 **Visibility** — cost trends and breakdowns, utilization statistics (avg/P95/σ), data freshness labels. Stale data is never presented as current.
> 🎯 **Optimization** — a rule engine (idle VMs, oversized instances, unused storage, cost anomalies) where every finding must pass evidence guards: a low average CPU with spiky P95 is *not* idle, active traffic blocks the finding regardless of cost.
> ✅ **Verification** — the part most tools skip: realized savings are measured from actual before/after cost windows, a negative result is stored honestly, and verification *refuses* when post-change data doesn't exist yet.
> 🛡️ **Governance** — human approval before any change, budgets with warning/critical thresholds, advisory policies, and an append-only audit log of every decision.
>
> Engineering discipline: 190+ tests, strict mypy/tsc, GitHub Actions with Gitleaks + Trivy, multi-arch non-root Docker, Prometheus metrics with SLI/SLO alerting, five documented incident exercises with MTTD/MTTR, and Terraform that is plan-reviewed but never auto-applied.
>
> Honest limitations: demo mode runs on deterministic synthetic data (the BigQuery/Monitoring providers are implemented but dormant until real data is enabled), and the forecast is a simple moving-average + trend blend — documented, not hidden.
>
> Repo and full write-up in the comments.

## Comment with repo link

> Repository: github.com/rifkyalmmin/cloud-cost-lab — includes a 5-minute demo script, ADRs, incident runbooks and a full docs set (20+ documents). Runs locally with `docker compose up -d` and zero GCP credentials.

## What NOT to claim (self-check before posting)

- Don't say "production" — say "production-grade practices" or "run like production".
- Don't say "saves money" — say "recommends and verifies savings with evidence".
- Don't say "AI-powered" without the read-only/keyword-context qualifier.
- Don't claim real GCP data — the providers are implemented but demo-first.
