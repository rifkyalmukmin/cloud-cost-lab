# Runbook: Forecast Engine Failure

## Alert
ForecastFailure (WARNING)

## Quick Check (< 2 minutes)

```bash
# Test forecast endpoint
curl http://localhost:8000/api/forecast

# Check logs
docker logs cloud-cost-lab-api 2>&1 | grep -i "forecast" | tail -20

# Check cost data availability
curl http://localhost:8000/api/cost/trend
```

## Diagnosis

### 1. Is there enough historical data?
Forecast requires minimum 7 days of cost data.
```bash
curl "http://localhost:8000/api/cost/trend?start_date=2026-08-01&end_date=2026-08-26"
# Check daily_costs count
```

### 2. Is cost data all zeros?
If billing export has no data yet, all costs are 0 → division by zero in regression.

### 3. Is it a calculation error?
Check logs for specific math errors (ZeroDivisionError, etc.)

## Resolution

### If insufficient data:
- Expected on new installations (< 7 days of data)
- API returns error message: "Insufficient historical data"
- Wait for billing data to accumulate

### If zero-data issue:
1. Verify billing export is producing data
2. If new project: wait for billing records
3. If DEMO_MODE=true: mock data should always work

### If calculation bug:
1. Check for edge cases: constant values, zero std_dev
2. Fix the calculation (add zero-guards)
3. Add test case
4. Deploy

## Prevention
- Guard: return error message when data < 7 days (already implemented)
- Guard: handle zero denominator in linear regression (already implemented)
- Tests cover: zero values, single day, constant values
