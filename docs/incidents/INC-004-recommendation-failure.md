# INC-004: Recommendation Engine Failure

## Severity
WARNING

## Detection
- Metric: recommendations_failed_total > 0
- Log: error in recommendation service
- SLI: recommendation_success_rate drops below 99%
- MTTD target: < 5 minutes

## Impact
- Recommendations may be incomplete or missing
- Potential savings not calculated for affected resources
- Dashboard shows partial optimization data
- Not a user-facing outage (API still responds)

## Timeline (Template)
| Time | Event |
|------|-------|
| T+0m | Recommendation rule throws error |
| T+0m | Error logged, metric incremented |
| T+5m | Alert fires if sustained |
| T+Xm | Engineer investigates |
| T+Xm | Root cause identified |
| T+Xm | Fix deployed |

## Root Cause Categories
1. New rule has a bug (division by zero, null handling)
2. Input data malformed (missing fields from provider)
3. Utilization data unavailable (monitoring provider down)
4. Resource data changed format
5. Memory error on large dataset

## Resolution Steps
1. Check logs for specific rule that failed
2. Identify the resource that caused the failure
3. Check input data (metrics, cost records) for anomalies
4. If rule bug: fix the rule, add test case, deploy
5. If data issue: check provider, handle edge case gracefully
6. Run recommendation pipeline manually to verify fix

## MTTD
Target: < 5 minutes
Metric incremented on each failure.

## MTTR
Target: < 2 hours
- Rule bug: fix + test + deploy (1-2 hours)
- Data issue: add null check, deploy (30 minutes)

## Prevention
- Comprehensive boundary condition tests (Phase 5)
- Null-safe rule implementations
- Each rule wrapped in try/except (log and skip, don't crash)
- Test with edge case data: null, 0, negative, missing fields

## Runbook
See: docs/runbooks/recommendation-failure.md
