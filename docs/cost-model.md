# Cost Model — Cloud Cost Lab

## Overview

The cost analytics engine aggregates GCP billing data and computes summaries, trends, and breakdowns by multiple dimensions.

## Data Sources

### Demo Mode (DEMO_MODE=true)
- Deterministic synthetic data generated with a fixed seed
- Simulates 90 days of billing across 8 resources
- Reproducible across restarts and tests

### Real Mode (DEMO_MODE=false)
- GCP Billing Export via BigQuery (Phase 9)
- Cloud Monitoring API for utilization (Phase 10)

## Mock Data Design

### Projects
| Project ID | Environment | Team |
|-----------|-------------|------|
| cloud-cost-lab-prod | production | platform |
| cloud-cost-lab-staging | staging | platform |
| cloud-cost-lab-dev | development | platform |

### Services
| Service | Category |
|---------|----------|
| Compute Engine | Compute |
| Cloud SQL | Database |
| Cloud Storage | Storage |
| Artifact Registry | Storage |

### Resources (8 total)
- 2 production VMs (e2-standard-4)
- 1 development VM (e2-standard-2)
- 1 idle VM (e2-medium) — unallocated owner
- 1 production Cloud SQL (db-custom-2-8192)
- 1 staging Cloud SQL (db-custom-1-4096)
- 1 Cloud Storage bucket
- 1 Artifact Registry repository

### Cost Generation

Each resource has a base daily cost. Variations are generated deterministically using SHA-256 hash of `resource_id:date:seed` to produce a uniform random factor between -12% and +15%.

Monthly growth: +8% per month from reference date.

A cost spike is injected on August 15 for the production API server (3.5x multiplier) to simulate an anomaly.

Development resources receive a 5% credit.

## API Endpoints

### GET /api/cost
Returns monthly summary:
- current_month_cost
- previous_month_cost
- mom_change_percent
- average_daily_cost
- projected_month_cost
- potential_savings
- currency
- data_freshness

### GET /api/cost/trend
Returns daily cost time series for a given range (default: 30 days).

### GET /api/cost/by-service
Returns cost breakdown grouped by GCP service.

### GET /api/cost/by-project
Returns cost breakdown grouped by GCP project.

### GET /api/cost/by-environment
Returns cost breakdown grouped by environment (production/staging/development).

## Calculations

### Month-over-Month Change
```
mom_change = ((current_month - previous_month) / previous_month) * 100
```

### Projected Month Cost
```
avg_daily = current_month_cost / days_elapsed
projected = avg_daily * 30
```

### Potential Savings (Estimate)
```
potential_savings = current_month_cost * 0.18
```
This is a placeholder heuristic. Real savings calculations come from the recommendation engine (Phase 4).

## Cost Dimensions

All endpoints support filtering by:
- start_date / end_date
- service
- project
- environment
- region (future)

Grouping dimensions:
- Service
- Project
- Environment
- Date (daily/weekly/monthly)
