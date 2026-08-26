# ADR-003: Demo Mode as First-Class Feature

## Status
Accepted

## Context
Cloud Cost Lab connects to GCP Billing Export (BigQuery) for real cost data. However:
- Not every developer has a GCP billing account
- BigQuery queries cost money
- Portfolio reviewers cannot run the app against our billing data
- Development and testing should not require GCP credentials
- Demo/interview scenarios need predictable data

## Decision
Implement Demo Mode (`DEMO_MODE=true`) as a first-class operating mode, not an afterthought.

The application uses a provider abstraction:

```
BillingDataProvider (interface)
├── RealBillingProvider  (GCP BigQuery)
└── MockBillingProvider  (synthetic data from data/mock/)
```

When `DEMO_MODE=true`:
- All data comes from synthetic JSON files
- No GCP credentials required
- Dashboard fully functional
- Recommendation engine produces real analysis on synthetic data
- Forecasting works on synthetic time series

## Alternatives Considered

### Record/replay from real GCP data
- Pro: Realistic data shapes
- Con: May contain sensitive billing info, harder to version control
- Verdict: Synthetic data is safer and more predictable

### In-memory fixtures only (no files)
- Pro: No file I/O
- Con: Hard to inspect/modify data, not shareable
- Verdict: JSON files in `data/mock/` are inspectable and versionable

### Separate demo application
- Pro: Clean separation
- Con: Code duplication, divergence risk
- Verdict: Same app, different provider — keeps behavior identical

## Trade-offs
- Mock data requires manual maintenance to stay realistic
- Demo scenarios may not cover all edge cases of real billing data
- Two code paths (real vs mock) must both be tested
- Benefit: zero-cost development, predictable demos, safe portfolio showcase

## Consequences
- `data/mock/` directory contains versioned synthetic data
- Provider selection happens at startup based on `DEMO_MODE` env var
- Tests primarily use mock provider (fast, deterministic)
- Integration tests for real provider run separately (requires GCP)
- README quick start uses demo mode by default
