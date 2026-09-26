# INC-001 — Billing data stale

| | |
| --- | --- |
| Severity | WARNING (critical if > 72h or MISSING) |
| Detection | Alert `BillingDataStale` (`billing_data_freshness_seconds > 86400`), surfaced by `GET /api/alerts` and the Overview freshness chip |
| Impact | Cost numbers age silently; budgets/anomalies/forecasts understate reality. Platform keeps serving last-known data, clearly labelled STALE |

## Timeline (scenario exercise, 2026-09-13 — synthetic demo, not a real outage)

1. T+0h — the billing export job in GCP silently stops (simulated by pinning the newest data day to 2026-09-05).
2. T+24h — `BillingDataStale` fires; MTTD measured **24h** (bounded by the SLO window; a 5-minute Prometheus `for: 30m` would catch it faster in real deployments).
3. T+24h30 — runbook step 1: confirm the export table's newest `_PARTITIONTIME` via `bq query`.
4. T+25h — runbook step 2: root cause in the Billing export settings (credentials expired / transfer paused).
5. T+26h — export re-enabled; next daily job completes. T+27h data current → alert resolves. MTTR measured **3h** from detection.

## Root cause
Export transfer paused upstream — the platform had no visibility into GCP-side job state (still true; the freshness SLI is the compensating control).

## Resolution & prevention
- Resolution: re-enable the export, verify `_PARTITIONTIME` advances daily.
- Prevention: freshness SLI + alert (implemented); weekly check of `bigquerydatatransfer` job history; `docs/gcp-setup.md` §6 checklist.
