# INC-001: Billing Data Stale

## Severity
WARNING (36h) → CRITICAL (48h)

## Detection
- SLI: billing_data_freshness_seconds exceeds threshold
- Alert: BillingDataStale / BillingDataCritical
- MTTD target: < 1 hour (automated metric check)

## Impact
- Dashboard shows outdated cost data
- Budget alerts may not fire on time
- Anomaly detection delayed
- Recommendations based on stale data

## Timeline (Template)
| Time | Event |
|------|-------|
| T+0h | Billing data age exceeds 36h |
| T+0h | Alert fires: BillingDataStale |
| T+Xh | Engineer investigates |
| T+Xh | Root cause identified |
| T+Xh | Resolution applied |
| T+Xh | Data freshness restored |

## Root Cause Categories
1. GCP Billing Export disabled or broken
2. BigQuery dataset permissions changed
3. Service account credentials expired
4. Network connectivity to GCP lost
5. BigQuery quota exceeded

## Resolution Steps
1. Check GCP Console → Billing → Billing Export status
2. Verify BigQuery dataset exists and is accessible
3. Test service account authentication
4. Check Cloud Cost Lab logs for query errors
5. If export disabled: re-enable in GCP Console
6. If permissions: re-grant bigquery.dataViewer
7. If credentials: rotate service account key or check Workload Identity

## MTTD
Target: < 1 hour (automated)
Metric: billing_data_freshness_seconds checked every 5 minutes

## MTTR
Target: < 4 hours
Most common fix: re-enable billing export or fix credentials (< 30 min)

## Prevention
- Monitor billing_data_freshness_seconds continuously
- Alert at 36h (warning) and 48h (critical)
- Regular credential rotation (or use Workload Identity Federation)
- Billing Export health check in CI/CD

## Runbook
See: docs/runbooks/billing-stale.md
