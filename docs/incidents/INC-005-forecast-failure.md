# INC-005: Forecast Engine Failure

## Severity
WARNING

## Detection
- Metric: forecast_failed_total > 0
- Log: error in forecast service
- API: /api/forecast returns error response
- MTTD target: < 5 minutes

## Impact
- 30-day cost forecast unavailable
- Budget breach prediction not generated
- Dashboard shows no forecast data
- Not a user-facing outage (API still responds for other endpoints)

## Timeline (Template)
| Time | Event |
|------|-------|
| T+0m | Forecast calculation throws error |
| T+0m | Error logged, metric incremented |
| T+5m | Alert fires |
| T+Xm | Engineer investigates |
| T+Xm | Root cause identified |
| T+Xm | Fix deployed |

## Root Cause Categories
1. Insufficient historical data (< 7 days)
2. All-zero cost data (division by zero in trend calculation)
3. Cost records corrupted or missing dates
4. Linear regression NaN (denominator = 0)
5. Memory error on large time series

## Resolution Steps
1. Check logs for specific error message
2. Check cost data availability: `GET /api/cost/trend`
3. Verify at least 7 days of cost records exist
4. If data insufficient: wait for more data, show "insufficient data" message
5. If calculation bug: fix the edge case, add test
6. Test forecast manually: `GET /api/forecast?reference_date=2026-08-26`

## MTTD
Target: < 5 minutes
Metric incremented on failure.

## MTTR
Target: < 1 hour
- Calculation bug: fix + deploy (30-60 minutes)
- Data issue: usually resolves when billing data refreshes

## Prevention
- Guard against insufficient data (< 7 days → return error, not crash)
- Guard against zero denominator in regression
- Test edge cases: 0 values, single day, constant values
- Forecast service already handles empty data gracefully

## Runbook
See: docs/runbooks/forecast-failure.md
