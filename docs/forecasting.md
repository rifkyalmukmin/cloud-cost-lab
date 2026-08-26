# Cost Forecasting — Cloud Cost Lab

## Overview

The cost forecasting system provides 30-day cost projections using hybrid methods (moving average + linear trend). **Forecasts are never presented as exact values** — they include confidence ranges (lower bound, expected, upper bound).

## Forecasting Methods

### 1. Moving Average (MA)
- Uses last 14 days of data
- Assumes stable spending pattern
- Good for short-term stability

### 2. Linear Trend (LT)
- Simple linear regression over historical data
- Captures growth/decline trends
- Good for trending patterns

### 3. Hybrid Forecast
- Weighted combination: 70% linear trend + 30% moving average
- Balances trend detection with stability
- Provides more robust projection than either method alone

## Confidence Bounds

Forecasts include ±1.5 standard deviation confidence margin (~87% confidence):

```
expected = 0.7 × linear_trend + 0.3 × moving_average
lower_bound = expected - 1.5 × std_dev
upper_bound = expected + 1.5 × std_dev
```

## API Endpoint

### GET /api/forecast

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| reference_date | date | Reference date (default: today) |
| days_ahead | int | Days to forecast (default: 30, max: 90) |

**Response:**
```json
{
  "period_start": "2026-08-26",
  "period_end": "2026-09-25",
  "method": "hybrid (linear trend + moving average)",
  "historical_days": 60,
  "forecast_days": 30,
  "daily_forecast": [
    {
      "date": "2026-08-27",
      "expected": 12.45,
      "lower_bound": 8.32,
      "upper_bound": 16.58,
      "confidence": "MEDIUM"
    }
  ],
  "monthly_summary": {
    "expected": 374.50,
    "lower_bound": 249.60,
    "upper_bound": 497.40,
    "range_description": "$249.60 - $497.40"
  }
}
```

## Data Requirements

| Minimum Data | Purpose |
|--------------|---------|
| 7 days | Minimum for any forecast |
| 14 days | Full moving average window |
| 30+ days | Better trend detection |
| 60 days | Optimal for 30-day forecast |

With insufficient data, returns:
```json
{
  "error": "Insufficient historical data (need at least 7 days)",
  "forecast": []
}
```

## Design Decisions

### Never Present as Exact

Forecasts are probabilistic, not deterministic. Always show:
- **Range**: "$249 - $497"
- **Expected value**: with clear indication it's an estimate
- **Confidence level**: MEDIUM (never HIGH for forecasts)

Never show:
- Single value without range
- "Will cost $X" statements
- HIGH confidence on future predictions

### Hybrid Method

Neither MA nor LT alone handles all patterns:
- MA misses trends
- LT over-reacts to noise

The 70/30 hybrid balances both.

### 30-Day Default

30 days aligns with:
- Monthly budgeting cycles
- GCP billing periods
- Actionable planning horizon

Longer forecasts (60-90 days) have lower confidence but are supported.

## Testing

22 new tests covering:
- Required fields (expected, lower_bound, upper_bound, confidence)
- Bound invariants (lower ≤ expected ≤ upper)
- Different forecast periods (7, 15, 30 days)
- Monthly summary aggregation
- API integration
