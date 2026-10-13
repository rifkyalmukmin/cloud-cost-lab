# monitoring/

Observability assets for Cloud Cost Lab.

**Status: partially implemented.** The application exposes Prometheus metrics,
structured JSON logs and in-process SLI/SLO + alert evaluation. This directory
contains the Prometheus alert/recording rules for a real deployment. There are
**no** Grafana dashboards, no Cloud Monitoring alert policies/dashboards, and no
Prometheus/Grafana containers in `docker-compose.yml` (8 GB RAM constraint; the
default stack is postgres + api).

## Contents

| File | What it is |
| --- | --- |
| `prometheus-rules.yml` | SLI recording rules + alerts for a Prometheus server scraping the API's `/metrics`. Mirrors the in-process evaluation in `apps/api/src/costlab/analytics/observability.py` (`evaluate_alerts`) |

The rules file has **not** been validated with `promtool` or loaded into a
running Prometheus from this repository (only checked to be valid YAML). Run
`promtool check rules monitoring/prometheus-rules.yml` before using it.

## What the application exposes

- `GET /metrics` — Prometheus text format:
  `http_requests_total`, `http_request_duration_seconds`,
  `billing_records_processed_total`, `billing_data_freshness_seconds`,
  `recommendations_generated_total`, `recommendation_runs_total{result}`,
  `forecast_runs_total`, `bigquery_query_duration_seconds`.
- `GET /api/freshness`, `GET /api/reliability`, `GET /api/alerts` — freshness
  (`FRESH` / `STALE`), SLI/SLO status and currently firing alerts, evaluated
  in-process without a Prometheus server.
- Structured JSON logs (timestamp, level, logger, message, operation,
  `duration_ms`, request id).

The metric list is defined in `analytics/observability.py`; check it if names
change (a rename of the recommendation counter was in flight when this was
written — re-check against the code after it merges).

## SLOs

| SLI | Objective |
| --- | --- |
| API availability (non-5xx / all requests) | >= 99.5% |
| Billing data freshness | < 24 h (older data is labelled `STALE`, never presented as current) |
| Recommendation pipeline success | >= 99% |

## Alerts in `prometheus-rules.yml`

`BillingDataStale`, `BillingDataMissing`, `APIAvailabilityLow`,
`RecommendationPipelineFailing`, `BigQueryQuerySlowOrFailing`. The first four
are also evaluated in-process (`/api/alerts`); the BigQuery alert exists only as a
Prometheus rule. Response steps: [`docs/runbook.md`](../docs/runbook.md); incident
write-ups: [`docs/incidents/`](../docs/incidents/).

Not implemented: alerts for cost anomalies and budget risk as monitoring alerts
(they are surfaced in the dashboard via `/api/anomalies` and `/api/budget`).

## Local use

```bash
curl -s localhost:8000/metrics | grep -E "^(http_requests_total|billing_data_freshness_seconds)"
curl -s localhost:8000/api/alerts
```

GCP side: Cloud Monitoring is used as a **data source** (utilization metrics, see
[`docs/gcp-monitoring.md`](../docs/gcp-monitoring.md)); the platform's own
alerting in Cloud Monitoring is not configured.
