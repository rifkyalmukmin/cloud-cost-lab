# data/mock/ — Demo Dataset

Synthetic billing, resource, and utilization data for demo mode (`DEMO_MODE=true`).

**Status: not implemented yet (Phase 1).** This directory will hold the mock dataset consumed by `MockBillingProvider` / `MockUsageProvider` in `apps/api`.

## Planned files

```text
projects.json         GCP-style project list with environments/labels
resources.json        VMs, disks, snapshots, Cloud SQL instances (incl. one idle VM,
                      one oversized VM, one unattached disk, one unlabelled resource)
cost.json             Daily cost records (CostRecord schema) with a rising cost
                      progression, e.g. $42 → $48 → $61/month, a Compute +35% spike,
                      and a budget-risk period
usage.json            CPU/memory/disk/network utilization time series (UsageRecord)
recommendations.json  Seed recommendations with evidence, potential savings, risk,
                      confidence, and approval state
forecast.json         Baseline series for the forecast feature
```

## Design intent

- Data must be **realistic but obviously synthetic** (no real project IDs, no real prices beyond plausible values).
- Scenarios must be deterministic so demo walkthroughs and tests are reproducible.
- The dataset exercises every demo scenario: idle VM, oversized VM, cost spike, budget risk, unused disk, dev scheduling, Cloud SQL underutilization, unallocated cost.
