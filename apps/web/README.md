# apps/web — Frontend Dashboard

Next.js + TypeScript frontend (Tailwind CSS + shadcn/ui) for Cloud Cost Lab.

**Status: not implemented yet (Phase 2).** This directory currently holds only the plan below — no application code.

## Planned routes

```text
/                Overview (current/previous month, MoM change, projected month end,
                 potential vs realized savings, budget status, data freshness)
/cost            Cost Explorer (filters, daily/weekly/monthly, breakdowns)
/resources       Resource Inventory (utilization, monthly cost, potential saving, risk)
/recommendations Evidence-based recommendations with approval state
/savings         Potential vs realized savings
/forecast        30-day forecast with range (never presented as exact values)
/budget          Budget status, warnings, forecast-over-budget risk
/utilization     Utilization analytics
/policies        Cost guardrails (PASS / WARNING / VIOLATION)
/reports         Generated reports
/ai              AI Cloud Cost Advisor (READ-ONLY, Phase 16)
/settings        Data source, demo mode, thresholds
```

## Ground rules

- Strict TypeScript.
- Every cost figure labelled with what it is: `estimated`, `potential`, `observed`, or `SIMULATION — NOT REALIZED SAVINGS`.
- Stale data is labelled `STALE`, never shown as current.
- Missing cost attribution is shown as `UNALLOCATED` — never guessed.
