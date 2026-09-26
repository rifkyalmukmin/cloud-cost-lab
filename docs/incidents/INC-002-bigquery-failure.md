# INC-002 — BigQuery failure

| | |
| --- | --- |
| Severity | WARNING (escalates to CRITICAL when freshness also breaches) |
| Detection | `GCPBillingError` in API logs with request id; alert `BigQueryQuerySlowOrFailing`; ingestion/refresh job failure |
| Impact | No new billing data reaches the platform; API keeps serving the last ingested snapshot (STALE-labelled) |

## Timeline (scenario exercise — simulated with a stubbed BigQuery client raising on query)

1. T+0 — BigQuery starts rejecting queries (quota / permission / schema change). Provider wraps the error: `GCPBillingError: BigQuery query failed (BadRequest): ...`.
2. T+0 — the refresh job fails loudly; **MTTD immediate** (in-process error), structured log carries `operation=bq_query` + duration histogram.
3. T+15m — runbook: check dry-run bytes log (schema change?), verify `roles/bigquery.dataViewer` still granted, check quota.
4. T+1h — root cause: table renamed after GCP changed export naming; `GCP_BILLING_TABLE` updated.
5. T+1h30 — next query succeeds, counter/histogram confirm. **MTTR 1.5h**.

## Root cause
External schema rename; the mapping fails at the boundary by design instead of writing half-valid facts.

## Resolution & prevention
- Resolution: align `GCP_BILLING_TABLE`/mapping with the new export schema.
- Prevention: `bq show --schema` after GCP notifications; dry-run byte log reviewed weekly; boundary validation ensures nothing partial is ingested (tested).
