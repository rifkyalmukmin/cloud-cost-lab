# ADR-003 — Demo / Mock Mode by Default

> Status: Accepted · Date: 2026-09-05 · Phase: 0

## Context

Cloud Cost Lab must teach and demonstrate FinOps concepts — cost aggregation, idle detection, rightsizing, budget risk, forecasting, anomaly response — **before** any real GCP billing integration exists (that is Phase 9). Constraints:

- Development must be possible with **zero cloud cost and zero GCP credentials** (safety contract in `docs/cost-safety.md`).
- Demos and tests must be **deterministic and reproducible** — a live cloud bill changes under you.
- The synthetic data must exercise specific teaching scenarios (idle VM, oversized VM, cost spike, budget risk, unallocated cost).

## Decision

- `DEMO_MODE=true` is the **default** configuration.
- Mock and real data access sit behind identical provider interfaces:

  ```text
  BillingDataProvider
  ├── MockBillingProvider    reads data/mock/*.json
  └── RealBillingProvider    GCP Billing Export → BigQuery   (Phase 9)

  UsageDataProvider
  ├── MockUsageProvider      synthetic utilization series
  └── RealUsageProvider      Cloud Monitoring                (Phase 9)
  ```

- The mock dataset lives in `data/mock/` (`projects.json`, `resources.json`, `cost.json`, `usage.json`, `recommendations.json`, `forecast.json`) with a deliberate cost progression (e.g., $42 → $48 → $61/month, a Compute +35% spike, one idle VM, one oversized VM, one unlabelled resource, one budget-risk period).
- No layer above the providers may know which mode is active; mode switching is configuration only.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Require real GCP billing from day one | Blocks all local work; violates the cost-safety contract; makes tests non-deterministic |
| Test fixtures only (no first-class mock mode) | Demo mode is a product requirement, not just a test utility — it needs the same runtime path |
| Hardcode fake data inside app code | Data must be replaceable and growable; files are editable without touching code |

## Trade-offs

- **Schema drift risk:** mock JSON can drift from the real Billing Export schema. Mitigation: the provider interface and record models (CostRecord/ResourceRecord/UsageRecord) define the contract; Phase 9 validates the real schema against those models and adds provider conformance tests.
- **Extra abstraction:** one interface + two implementations for data we could "just load". Accepted — the mock/real switch is the architecture's most important seam.
- **Fictional numbers:** mock savings/costs are illustrative. Every UI/API label must therefore say *estimated/potential/simulation* — mock mode makes honesty about data provenance a first-class feature.

## Consequences

- Positive: the entire product (dashboard, analytics, recommendations, approval workflow) is buildable and demoable offline, free, and safely; tests never flake on live data.
- Negative: Phase 9 will require a schema-reconciliation pass that is easy to underestimate; a `RealBillingProvider` conformance test is planned for that phase.
- Rule added: demo scenarios must remain reproducible with a single `docker compose up` — no manual data editing in demo flows.
