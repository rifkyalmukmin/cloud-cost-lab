# 5-Minute Demo Script — Cloud Cost Lab

> Setup beforehand: `cp .env.example .env && docker compose up -d`, then `cd apps/web && npm ci && npm run dev` (or `next start`). The stack serves demo data automatically.
> For a clean lifecycle state, reset once first: `cd apps/api && python -m costlab.seed --force` (re-seeds facts and re-runs the recommendation engine).
> Every screen also shows where the honest caveat lives — pointing at those is part of the demo.

## 0:00–0:45 — Overview (the headline)

Open `http://localhost:3000/`.

- Current Month Cost (MTD), Previous Month, MoM change — note the badge *"5 days compared on both sides"*: the comparison is fair, not partial-vs-full.
- Projected Month-End labelled **estimate**; the STALE chip with data age — *"the platform refuses to present old data as current."*
- Potential Savings card now shows the live estimate from the recommendation engine — with the honest note that potential is an *estimate*, not realized.

## 0:45–1:30 — Cost Explorer (drill-down)

Open **Cost Explorer**.

- Filter by service = Compute Engine; show daily/weekly/monthly granularity switch.
- Breakdown tables respect filters; cost records are server-side paginated.
- Line: *"Every number comes from the API — nothing is hardcoded in the UI."*

## 1:30–2:30 — Resources & Utilization (cost + performance)

Open **Resources**, then **Utilization**.

- Resources: monthly cost joined with CPU/memory meters; the legacy sandbox shows **UNALLOCATED** — *"missing ownership is surfaced, never guessed."*
- Utilization: Cost-vs-Utilization chart with the 20%/80% evidence lines; avg/P95/stddev per resource — *"P95 because averages hide spikes."*
- Point at the amber **low** signals on the dev VMs — that is the evidence the recommendation engine will use.

## 2:30–3:30 — Recommendations (evidence + human approval)

Open **Recommendations**.

- Five findings: an **Idle** VM, two **Oversized** (with savings math), two **Cost anomalies**. (If one shows VERIFIED from earlier testing, that is the demo's best line — point to its realized number on the Savings page.)
- Open a detail: Problem → Evidence → Recommendation → Potential Savings → Risk → Confidence → Effort. *"Cost alone never makes a recommendation — CPU, duration and traffic guards must pass."*
- Click **Approve** (live) — audit trail records the decision. *"The platform never executes anything itself."*

## 3:30–4:15 — Savings (potential vs realized)

Open **Savings**.

- Potential vs Approved vs Implemented vs Verified vs **Realized**.
- *"Realized only exists after verification: actual net cost 30 days before vs after the implementation date — and a negative result is stored as measured, never clamped."*
- If asked: verification refuses with 409 when post-change data doesn't exist yet.

## 4:15–4:45 — Forecast & Budget (uncertainty + guardrails)

Open **Forecast**, then **Budget**.

- Forecast: 30-day expected with a shaded range and confidence — *"never a single certain number."*
- Budget: $50 limit, HEALTHY today, but the projection exceeds it — the honest budget-risk story.

## 4:45–5:00 — AI Advisor (read-only)

Ask the advisor (API or UI hook): *"Why did cost increase?"*

- Answer with Summary / Evidence / Likely Cause / Recommendation / Savings / Risk / Confidence.
- *"Read-only by construction, refuses prompt injection, and says 'insufficient evidence' when the data can't support an answer."*

## Closing line

*"The complete FinOps loop — visibility, allocation, optimization, verification, governance — built test-first with 198 backend tests, full IaC, and a CI pipeline that gates every change. And it never touches infrastructure without a human."*

## Backup answers

- *"Is the data real?"* — No, deterministic synthetic data by design; the GCP BigQuery/Monitoring providers are implemented and tested against stubs, activation is a documented manual step.
- *"Did you apply the Terraform?"* — No; plan was validated against the real project (5 resources), apply is deliberately withheld.
- *"What would you build next?"* — Real-GCP enablement, scheduled utilization rollups for scale, structured LLM output parsing, unit economics.
