# INC-005 — Forecast failure

| | |
| --- | --- |
| Severity | LOW/WARNING |
| Detection | `forecast_runs_total{result="failure"}` increments; `GET /api/forecast` returns 500 or `sufficient_data: false` unexpectedly |
| Impact | The forecast page shows its error/insufficient state; budgets and anomaly views unaffected |

## Timeline (scenario exercise — simulated with a corrupted series: a non-numeric value reaching the trend fit)

1. T+0 — `GET /api/forecast` 500s; **MTTD immediate** (route error + structured log with request id).
2. T+5m — runbook: check `forecast_runs_total{result}` counters; replay the query with the same filters; inspect the daily series for a bad value.
3. T+15m — root cause (exercise): a malformed usage/cost row produced a non-float daily bucket; the fit raised.
4. T+25m — boundary validation rejects malformed rows before aggregation (provider/loader already do — the injected case came from a hand-edited test DB row). **MTTR ~25m**.
5. T+30m — forecast restored; `forecast_runs_total{result="success"}` resumes.

## Root cause
Dirty data reached the forecast path through a manual DB edit bypassing ingestion validation — the pipeline's boundary checks were bypassed, not broken.

## Resolution & prevention
- Resolution: clean the row; re-run.
- Prevention: all data enters through the validated provider/loader path (pydantic boundary); forecast failures are counted per result so a broken horizon is visible in the reliability view.

## MTTD / MTTR summary (all five incidents)

| Incident | MTTD | MTTR |
| --- | --- | --- |
| INC-001 Billing stale | 24h (SLO window) | 3h |
| INC-002 BigQuery failure | immediate | 1.5h |
| INC-003 API outage | ~1m (external probe) | 10m |
| INC-004 Recommendation failure | immediate | ~40m |
| INC-005 Forecast failure | immediate | ~25m |

These are **scenario exercises on the demo stack** (measured while scripting the failure), not real outages — the platform has had no production incident.
