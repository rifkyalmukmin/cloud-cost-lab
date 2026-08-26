# Anomaly Detection — Cloud Cost Lab

## Overview

The anomaly detection system identifies unexpected cost increases using z-score analysis with a rolling average baseline. Anomalies are flagged when costs deviate significantly from historical patterns.

## Detection Method

### Rolling Average Baseline
- 14-day rolling window
- Calculates mean and standard deviation
- Baseline adapts to cost trends

### Z-Score Analysis
- Measures how many standard deviations above baseline
- `z_score = (actual - baseline) / std_dev`
- Threshold: z-score > 2.0 (~95% confidence)

### Severity Levels
| Z-Score | Severity | Meaning |
|---------|----------|---------|
| 2.0-3.0 | MEDIUM | Notable deviation |
| > 3.0 | HIGH | Extreme deviation |

## Anomaly Fields

| Field | Type | Description |
|-------|------|-------------|
| date | date | When anomaly occurred |
| actual | float | Actual cost observed |
| expected | float | Baseline cost (rolling average) |
| difference | float | actual - expected (absolute) |
| percentage_change | float | (difference / expected) × 100 |
| z_score | float | Number of std deviations above baseline |
| severity | str | MEDIUM or HIGH |
| confidence | str | HIGH (for detected anomalies) |
| top_service | str | Service contributing most to the spike |
| top_service_cost | float | That service's cost on the anomaly date |
| top_project | str | Project contributing most |
| top_project_cost | float | That project's cost |
| top_resource | str | Resource contributing most |
| top_resource_cost | float | That resource's cost |

## API Endpoint

### GET /api/anomalies

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| reference_date | date | End date for analysis (default: today) |
| lookback_days | int | Days to analyze (default: 30, min: 7, max: 90) |

**Response:**
```json
{
  "period_start": "2026-07-28",
  "period_end": "2026-08-26",
  "lookback_days": 30,
  "method": "z-score (rolling average baseline)",
  "threshold": "z-score > 2.0",
  "anomalies": [
    {
      "date": "2026-08-15",
      "actual": 45.30,
      "expected": 12.50,
      "difference": 32.80,
      "percentage_change": 262.4,
      "z_score": 3.42,
      "severity": "HIGH",
      "confidence": "HIGH",
      "top_service": "Compute Engine",
      "top_service_cost": 38.20,
      "top_project": "Cloud Cost Lab Production",
      "top_project_cost": 42.10,
      "top_resource": "vm-prod-api-01",
      "top_resource_cost": 11.20
    }
  ],
  "total_anomalies": 1
}
```

## Attribution

Each anomaly includes:
- **top_service**: which GCP service caused the spike
- **top_project**: which project
- **top_resource**: which specific resource

This enables immediate investigation.

## Use Cases

### 1. Cost Spike Investigation
When costs jump unexpectedly, anomalies show:
- When it happened
- How much it increased (absolute + %)
- Which resource caused it

### 2. Budget Breach Prevention
Anomalies detected early enable proactive response before budget is exceeded.

### 3. Configuration Drift Detection
Sudden cost changes often indicate:
- Unintended resource creation
- Configuration changes (instance resize)
- Traffic spikes
- Service misconfiguration

## Design Decisions

### Z-Score Over Fixed Threshold

Fixed thresholds (e.g., "alert if daily cost > $50") are brittle:
- Too sensitive for high-spend projects
- Too loose for low-spend projects

Z-score adapts to the project's baseline:
- $5 → $15 = 200% increase, z-score ~3.0 → HIGH severity
- $100 → $115 = 15% increase, z-score ~0.5 → not flagged

Same relative deviation, different absolute amounts.

### Rolling Window

14-day rolling window balances:
- Enough data for stable baseline
- Recent enough to adapt to trends

Prevents:
- False positives from one-off spikes entering baseline
- Stale baselines from old patterns

### Attribution Included

Anomaly without attribution requires manual investigation.

Including top_service/project/resource enables immediate action:
- "Compute Engine spike on vm-prod-api-01"
- Jump directly to that resource's metrics

## Testing

17 new tests covering:
- Required fields
- Severity thresholds
- Attribution fields (service, project, resource)
- Invariants (actual > expected, z_score > 2.0)
- API integration
- Insufficient data handling

## Integration with CostAnomalyRule

The recommendation engine's `CostAnomalyRule` triggers on cost_change > 50%.

This anomaly detection service is **more sensitive**:
- Detects smaller deviations (z-score > 2.0 ≈ 95% confidence)
- Provides daily granularity
- Includes full attribution

Both complement each other:
- Anomaly detection: real-time monitoring
- CostAnomalyRule: recommendation generation
