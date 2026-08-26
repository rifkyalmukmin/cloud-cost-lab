# INC-002: BigQuery Query Failure

## Severity
CRITICAL

## Detection
- Metric: bigquery_query_duration_seconds shows errors
- Log: "BigQuery query failed" in structured logs
- SLI: recommendation_success_rate drops
- MTTD target: < 5 minutes (request-level error)

## Impact
- Cost data unavailable
- Recommendations cannot be generated
- Forecasting fails
- Anomaly detection fails
- Dashboard shows stale or no data

## Timeline (Template)
| Time | Event |
|------|-------|
| T+0m | BigQuery query returns error |
| T+0m | Error logged, metric incremented |
| T+5m | Alert fires if sustained |
| T+Xm | Engineer investigates |
| T+Xm | Root cause identified |
| T+Xm | Resolution applied |

## Root Cause Categories
1. BigQuery service outage (rare, GCP issue)
2. Query quota exceeded
3. Table/dataset deleted or renamed
4. Permission revoked
5. Query syntax error after code change
6. Table schema changed (billing export update)

## Resolution Steps
1. Check GCP Status Dashboard for BigQuery outage
2. Check Cloud Cost Lab logs for specific error message
3. Verify table exists: `bq show billing_export.table_name`
4. Test query manually: `bq query --dry_run "SELECT 1 FROM table"`
5. Check quotas: GCP Console → BigQuery → Quotas
6. If permissions: re-grant roles to service account
7. If table renamed: update GCP_BILLING_TABLE env var

## MTTD
Target: < 5 minutes
Error is detected on the failing request itself.

## MTTR
Target: < 1 hour
- GCP outage: wait for resolution (outside our control)
- Permission/config issue: < 30 minutes to fix

## Prevention
- Use partition filters to avoid query cost spikes
- Monitor BigQuery quotas
- Test queries in CI/CD with --dry_run
- Keep GCP_BILLING_TABLE as environment variable (easy to update)

## Runbook
See: docs/runbooks/bigquery-failure.md
