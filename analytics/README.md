# analytics/

Cost & usage analysis modules for Cloud Cost Lab.

**Status: not implemented yet.** Subdirectories are placeholders for the phases listed below. These modules are consumed by `apps/api` (they are plain Python packages, not separate services — see `docs/decisions/ADR-001-architecture.md`).

| Directory | Purpose | Phase |
| --- | --- | --- |
| `cost/` | Aggregation (by service/project/environment/region/date), WoW & MoM change, top resources, unallocated cost | Phase 2 |
| `utilization/` | CPU/memory/disk/network usage analysis, linkage between cost and utilization | Phase 3 |
| `recommendations/` | Pluggable rule engine: `IdleComputeRule`, `OversizedComputeRule`, `UnusedDiskRule`, `StorageRetentionRule`, `CloudSQLRightsizingRule`, `BudgetRiskRule`, `CostAnomalyRule`, … Each rule exposes `evaluate()`, `explain()`, `calculate_saving()`, `calculate_risk()`, `confidence()` | Phase 4+ |
| `forecasting/` | Moving average / linear regression 30-day forecast with a range (never exact-only) | Phase 6 |

## Ground rules

- Business logic here must be unit-tested (pytest).
- Every recommendation answers: what is wrong, what evidence supports it, how much could be saved (potential, not guaranteed), what the risk is, effort, who approves, next step.
- Priority scoring is a **project-specific optimization priority score**, not an industry standard.
