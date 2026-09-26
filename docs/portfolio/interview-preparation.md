# Interview Preparation — Cloud Cost Lab

> Answers are grounded in what is actually implemented. Where the honest answer is a limitation, the limitation is the answer.

---

## 1. What problem does this solve?

Cloud consoles show costs but don't join them to utilization or performance, don't quantify uncertainty, and don't enforce a human approval loop. My platform links billing data with resource utilization, detects waste with measured evidence (idle VMs, oversized instances, cost spikes), estimates potential savings, verifies *realized* savings from actual before/after data, and requires human approval before any change.

## 2. Why FinOps?

Because engineering decisions — instance types, schedules, retention — *are* financial decisions, and engineers usually can't see their impact. FinOps is where SRE thinking (SLIs, error budgets) meets cost: I treat "potential savings" like a hypothesis and "realized savings" like a measurement.

## 3. Walk me through the architecture.

Provider abstraction at the top: `BillingDataProvider` and `MonitoringDataProvider` with a mock implementation (deterministic demo data) and GCP implementations (BigQuery billing export, Cloud Monitoring) behind the same contract — nothing above the providers knows which mode is active. Facts land in PostgreSQL (Alembic migrations). An analytics layer computes everything in SQL (aggregations, P95 via `percentile_cont`, z-scores). A rule engine turns that into recommendations; a Next.js dashboard renders it; Prometheus metrics and structured JSON logs observe it.

## 4. How do you prevent false-positive recommendations?

Evidence guards in every rule. Example — the idle rule requires: average CPU < 5%, **P95 ≤ 20%** (a low average with spiky P95 is a periodic batch workload, not idle), network traffic below a floor, at least 7 days of samples, and actual cost evidence. Missing data means silence, never a guess. The oversized rule additionally requires a stable stddev and P95 headroom. These boundaries are unit-tested: CPU exactly 5% or exactly 20% does *not* fire.

## 5. Distinguish potential vs realized savings.

Potential savings are an estimate from pre-change evidence. Realized savings are measured after the change: I compare mean daily net cost 30 days before vs after the implementation date (minimum 7 after-days required) and store the monthly-equivalent difference. If costs went up, the negative number is stored as measured. If post-change data doesn't exist, verification returns 409 — the saving stays potential. Estimates are never relabelled.

## 6. How do you avoid expensive BigQuery queries?

Partition filter on `_PARTITIONTIME` plus the same bound on `usage_start_time`, an explicit column whitelist (no `SELECT *`), a day-range cap and row cap, query parameters instead of string interpolation, and a dry run first that logs bytes-to-be-scanned. All of it is asserted in tests, not just documented.

## 7. How do you handle missing labels or metrics?

Three states, never conflated: a 0 is an observation (kept in stats), a null is a gap (excluded from aggregates), and a metric with no samples is "missing" — surfaced through `missing_metrics`, never rendered as 0. Missing ownership renders as UNALLOCATED, never guessed. The public-database policy reports "cannot verify" instead of a false pass.

## 8. How does the AI advisor stay safe?

Read-only by construction: it's an endpoint that returns text — no tools, no execution path. Questions are untrusted data: sanitized, length-capped, screened for instruction-override markers and refused. When the context can't support an answer it says "Insufficient evidence". The default advisor is deterministic (keyword intents over structured context) so it's reproducible; the optional LLM provider gets a safety system prompt and its output is labelled "verify before use".

## 9. How do you know the system is healthy?

Prometheus metrics (requests, latency, ingestion counts, freshness gauge, engine runs, BigQuery duration), SLIs compared against SLOs (availability ≥ 99.5%, freshness < 24h, recommendation success ≥ 99%) via `/api/reliability`, alerts linked to runbooks, structured JSON logs with request-id correlation. The freshness SLO currently *fails* on the demo dataset and the UI shows that honestly.

## 10. Why is Terraform never applied?

It's validated (`fmt`, `validate`, and a real `plan` against the project: 5 resources, 0 destroy) but apply is a human decision with a billing impact. The plan output, cost estimate (~$0–1/month), and destroy strategy are documented. Same philosophy as the whole platform: the system proposes, a human decides.

## 11. What was the hardest bug?

The recommendation engine originally aggregated usage after joining cost records — a resource with several cost lines per day fanned out usage rows and silently corrupted every count, average and P95. Fixed by computing usage stats and cost in separate subqueries joined per resource. Lesson: in analytics, *join order is correctness*.

## 12. What would you change in a real production system?

Scheduled utilization rollups instead of on-demand aggregates; per-team policy/budget overrides; a real secrets and identity setup with Workload Identity Federation; multi-replica API with a shared metrics registry; causal attribution support for savings verification.

## 13. Numbers you can state confidently

- 198 backend tests (pytest, strict mypy with zero issues) + 8 frontend tests.
- ~40 documented endpoints across cost, resources, utilization, recommendations, savings, budget, policies, forecast, anomalies, freshness, reliability, alerts, AI.
- 5 recommendation rules, 5 governance policies, 5 incident documents with exercised MTTD/MTTR.
- Demo dataset: 12 resources, 97 days, ~$170 modelled spend, one unallocated resource, one idle VM, two cost-spike episodes.
- 0 billable GCP resources created by the project; Terraform plan = 5 resources, 0 destroy.
