# Utilization Analysis — Cloud Cost Lab

## Overview

Utilization analysis links resource cost with utilization metrics to identify efficiency opportunities. It computes statistics (avg, min, max, p95), detects patterns (low, high, unstable, missing), and provides evidence without making automatic recommendations.

## Metrics Tracked

| Metric | Type | Description |
|--------|------|-------------|
| CPU | float (%) | CPU utilization percentage |
| Memory | float (%) | Memory utilization percentage |
| Disk | float (%) | Disk utilization percentage |
| Network In | float (MB) | Inbound network traffic |
| Network Out | float (MB) | Outbound network traffic |

## Statistics Computed

For each metric (CPU, memory, disk), the system computes:
- **avg**: mean value over the period
- **min**: minimum observed value
- **max**: maximum observed value
- **p95**: 95th percentile (useful for identifying spikes)

## Pattern Detection

The system analyzes utilization patterns and categorizes each resource:

| Pattern | Condition | Evidence |
|---------|-----------|----------|
| **low** | avg < 15% | Resource is underutilized |
| **high** | avg > 85% | Resource may be overloaded |
| **unstable** | variance > 60% (max - min > 60) | Unstable workload |
| **normal** | 15% ≤ avg ≤ 85% and variance ≤ 60% | Within normal range |
| **missing** | No metrics available | N/A for storage or metrics unavailable |

**Important**: These patterns provide **evidence only**. No automatic recommendations are generated in this phase. Engineers interpret the evidence and decide on actions.

## API Endpoints

### GET /api/utilization

Get utilization summary across all resources.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start_date | date | Start date (default: 30 days ago) |
| end_date | date | End date (default: today) |

**Response:**
```json
{
  "period_start": "2026-07-28",
  "period_end": "2026-08-26",
  "total_resources": 8,
  "low_utilization_count": 2,
  "high_utilization_count": 0,
  "unstable_count": 0,
  "missing_metrics_count": 2,
  "resources": [
    {
      "resource_id": "vm-prod-api-01",
      "name": "prod-api-server-01",
      "service": "Compute Engine",
      "environment": "production",
      "monthly_cost": 96.00,
      "cpu": {
        "avg": 62.0,
        "min": 43.4,
        "max": 80.6,
        "p95": 78.2
      },
      "memory": {
        "avg": 71.0,
        "min": 56.8,
        "max": 85.2,
        "p95": 83.0
      },
      "disk": {...},
      "cpu_pattern": {
        "status": "normal",
        "evidence": "Average CPU is 62.0% — within normal range"
      },
      "memory_pattern": {
        "status": "normal",
        "evidence": "Average memory is 71.0% — within normal range"
      }
    }
  ]
}
```

### GET /api/utilization/{resource_id}

Get detailed utilization for a specific resource with history.

**Response includes:**
- Resource metadata
- Statistics (cpu, memory, disk with avg/min/max/p95)
- Pattern analysis (cpu_pattern, memory_pattern)
- Utilization history (30-day daily records)

**404** if resource not found.

### GET /api/utilization/cost-vs-utilization/data

Get cost vs utilization data for scatter plot visualization.

**Response:**
```json
{
  "period_start": "2026-08-01",
  "period_end": "2026-08-26",
  "data": [
    {
      "resource_id": "vm-prod-api-01",
      "name": "prod-api-server-01",
      "service": "Compute Engine",
      "environment": "production",
      "cost": 83.20,
      "cpu_avg": 62.0,
      "memory_avg": 71.0
    }
  ]
}
```

## Frontend

### /utilization — Utilization Analysis Page

**Summary Cards:**
- Total Resources
- Low Utilization (count)
- High Utilization (count)
- Unstable (count)

**Cost vs CPU Utilization Chart (Scatter Plot):**
- X-axis: CPU utilization (%)
- Y-axis: Monthly cost ($)
- Bubble size: proportional to cost
- Interpretation guide: Resources in the top-left quadrant (low CPU, high cost) are optimization candidates

**Utilization Table:**
Shows all resources with:
- Resource name + service
- Environment
- Monthly cost
- CPU stats (avg, min, max, p95)
- CPU pattern badge + evidence
- Memory stats (avg, min, max, p95)
- Memory pattern badge + evidence

Pattern badges are color-coded:
- **low**: amber
- **high**: red
- **unstable**: orange
- **normal**: green
- **missing**: gray

## Design Decisions

### Evidence, Not Recommendations

This phase intentionally provides **evidence only**:
- Pattern detection identifies anomalies
- Evidence explains what the data shows
- Engineers interpret and decide on actions
- Phase 4 (recommendation engine) will build on this evidence

### P95 vs Max

P95 is more useful than max for identifying typical peak behavior:
- max can be a single outlier
- p95 represents the "normal peak" (95% of values are below this)
- Used to distinguish between true high utilization and transient spikes

### Null Handling

Storage resources (Cloud Storage, Artifact Registry) have null CPU/memory:
- They don't have compute metrics
- Disk utilization is still tracked
- Pattern status = "missing" for CPU/memory

### Zero Values

Test coverage includes:
- Empty lists (no data) → all stats null
- Zero values (idle resource) → stats computed as 0
- Single value (constant load) → avg = min = max = p95

## Example Interpretations

| Pattern | Evidence | Possible Action |
|---------|----------|-----------------|
| low CPU 3% | Underutilized | Consider scheduling, downsizing, or decommissioning |
| high CPU 90% | May be overloaded | Monitor for performance issues, consider upsizing |
| unstable CPU 10%-90% | Unstable workload | Investigate autoscaling, workload patterns |
| normal CPU 60% | Within normal range | No immediate action needed |
| missing CPU | No metrics | Expected for storage, check if compute metrics missing |

## Testing

78 backend tests passing, covering:
- Aggregation across 8 resources
- Statistics computation (avg, min, max, p95)
- Pattern analysis (low, high, unstable, normal, missing)
- Null/zero/single-value edge cases
- Date range filtering
- Missing resource (404)
- Storage resources (null CPU/memory)
