# ADR-004 — GCP Integration Strategy

> Status: Accepted · Date: 2026-09-05 · Phase: 0 (integration itself is Phase 9)

## Context

The project targets GCP FinOps, so eventually it must consume **real** GCP data. But GCP integration has two faces:

1. It is the core learning goal (Billing Export, BigQuery, Monitoring, IAM).
2. It is the project's biggest **cost and security risk surface** (query costs, credentials, permissions).

Decisions made now (Phase 0) shape what Phase 9 will look like.

## Decision

- **GCP-first, deferred integration.** Real data lands in Phase 9; until then mock mode (ADR-003) is the only data path.
- **Billing Export → BigQuery** is the canonical cost source, configured via environment variables only:
  `GCP_BILLING_PROJECT`, `GCP_BILLING_DATASET`, `GCP_BILLING_TABLE`.
- **Least-privilege, separated identities:**
  - `cost-data-reader` — read-only on billing export data;
  - `monitoring-reader` — read-only on metrics;
  - `cost-optimizer` — separate identity for explicitly bounded future actions; never broad `Owner`/`Editor` for convenience.
- **No service account keys in git — ever.** Local auth via Application Default Credentials; CI via Workload Identity Federation when feasible; app secrets via Secret Manager.
- **BigQuery cost protection is mandatory:** partition/date filters, explicit column selection, early aggregation, dry-run byte estimates, no repeated full-table scans. Documented in `docs/bigquery-cost.md` (Phase 9).
- Documentation for billing export enablement, required permissions, expected schema, data freshness, privacy, and query cost is a Phase 9 deliverable, not an afterthought.

## Alternatives considered

| Alternative | Why rejected / deferred |
| --- | --- |
| AWS (Cost Explorer / CUR) or Azure | Author's account and learning targets are GCP; multi-cloud is a future provider implementation behind the same interfaces |
| Manual CSV billing export | Zero-setup, but no reproducibility, no partition filtering, and none of the BigQuery skills this project exists to build |
| Polling GCP APIs (Cloud Billing Catalog, per-service APIs) | Incomplete cost attribution compared to Billing Export; higher API surface to secure |
| One broad service account with Editor | Single point of failure; violates least privilege; makes audit meaningless |

## Trade-offs

- **BigQuery cost:** queries over billing data cost money. Mitigated by the query rules above and by aggregating into PostgreSQL instead of re-querying BigQuery repeatedly.
- **Delayed integration:** UI/analytics are built against the assumed schema before real data validates it. Mitigated by provider conformance tests planned for Phase 9 (ADR-003).
- **Data freshness/privacy:** real billing export lags and contains project-level detail. Freshness is surfaced as `FRESH/STALE`; privacy notes (what the data reveals) are documented at integration time.

## Consequences

- Positive: real-data integration becomes a bounded, pre-planned task with an explicit security model; the demo path never depends on it.
- Negative: some Phase 9 work is speculation until a real export exists; a schema reconciliation pass is budgeted for that phase.
- Guardrail: no GCP resource for this project is created before the 7-question cost review in `docs/cost-safety.md` is answered, and budget alerts exist before anything billable runs.
