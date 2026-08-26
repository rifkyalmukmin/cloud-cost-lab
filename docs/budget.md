# Budget Monitoring — Cloud Cost Lab

## Overview

The budget monitoring system tracks spending against defined budgets and generates alerts when thresholds are breached. **No automatic destructive actions are taken** — only warnings and recommendations are provided.

## Budget Configuration

```json
{
  "id": "monthly-budget-001",
  "name": "Monthly Cloud Budget",
  "scope": "global",
  "period": "monthly",
  "limit": 500.00,
  "warning_threshold": 70.0,
  "critical_threshold": 90.0,
  "currency": "USD"
}
```

## Budget Status Levels

| Status | Condition | Description |
|--------|-----------|-------------|
| **HEALTHY** | < 70% | Spending is well within budget |
| **WARNING** | 70-89% | Approaching warning threshold |
| **CRITICAL** | 90-99% | Budget breach imminent |
| **EXCEEDED** | ≥ 100% | Budget has been exceeded |

## Threshold Testing

All boundary conditions tested:
- 69% → HEALTHY
- 70% → WARNING
- 89% → WARNING
- 90% → CRITICAL
- 99% → CRITICAL
- 100% → EXCEEDED
- 101% → EXCEEDED

## API Endpoint

### GET /api/budget

Get current budget status.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| reference_date | date | Reference date for calculation (default: today) |

**Response:**
```json
{
  "budget": {
    "id": "monthly-budget-001",
    "name": "Monthly Cloud Budget",
    "scope": "global",
    "period": "monthly",
    "limit": 500.0,
    "warning_threshold": 70.0,
    "critical_threshold": 90.0,
    "currency": "USD"
  },
  "current": {
    "spend": 345.67,
    "utilization_pct": 69.13,
    "remaining": 154.33,
    "status": "HEALTHY"
  },
  "projected": {
    "spend": 432.50,
    "utilization_pct": 86.50,
    "status": "WARNING"
  },
  "alerts": [
    {
      "severity": "WARNING",
      "message": "Projected to reach 86.5% by month end",
      "recommendation": "Current spending trend will breach budget. Consider implementing cost-saving measures now."
    }
  ]
}
```

## Alert Severity Levels

| Severity | Trigger |
|----------|---------|
| **CRITICAL** | Budget exceeded or critical threshold breached |
| **WARNING** | Warning threshold breached or projection shows future breach |

## Recommendations

Alerts include actionable recommendations:
- **EXCEEDED**: "Review spending immediately. Identify high-cost resources and implement cost-saving recommendations."
- **CRITICAL**: "Budget breach imminent. Pause non-essential resource creation and review optimization opportunities."
- **WARNING**: "Monitor spending closely and review cost optimization recommendations."
- **Projected breach**: "Current spending trend will breach budget. Consider implementing cost-saving measures now."

## Design Decisions

### No Automatic Actions

The system:
- ✓ Tracks spending vs budget
- ✓ Calculates utilization percentage
- ✓ Generates alerts
- ✓ Provides recommendations
- ✗ Does NOT stop resource creation
- ✗ Does NOT delete resources
- ✗ Does NOT downsize instances
- ✗ Does NOT modify infrastructure

Engineers review alerts and decide on actions.

### Current + Projected

Both current and projected spending are tracked:
- **Current**: actual spend so far this period
- **Projected**: extrapolated spend for full period based on current trend

This enables proactive alerting before breach occurs.
