# monitoring/

Observability assets for Cloud Cost Lab (dashboards, alert rules, SLO definitions).

**Status: not implemented yet (Phase 10).** Only this plan exists.

## Planned content

- SLI/SLO definitions:
  - API availability >= 99.5%
  - cost data freshness < 24h (older data is labelled `STALE`, never shown as current)
  - recommendation pipeline success >= 99%
- Application metrics: `http_requests_total`, `http_request_duration_seconds`, `cost_records_processed_total`, `recommendations_generated_total`, `forecast_runs_total`, `billing_query_duration_seconds`.
- Structured JSON logs (timestamp, level, service, operation, duration_ms).
- Alert conditions: API failures, billing query failures, stale data, pipeline failures, cost anomalies.

Tools: Google Cloud Monitoring/Logging first; Prometheus/Grafana only where they add clear value for local/demo visualization (8 GB RAM constraint).
