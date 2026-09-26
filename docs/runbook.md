# Operations Runbook — Cloud Cost Lab

> Status: living document · Date: 2026-09-13
> Procedures for the alerts defined in `monitoring/prometheus-rules.yml` and evaluated live by `GET /api/alerts`. Each procedure ends with how to verify recovery. MTTD/MTTR references point at `docs/incidents/`.

---

## 0. Quick triage

```bash
docker compose ps                              # is everything up?
curl -s localhost:8000/health | jq             # liveness
curl -s localhost:8000/ready | jq              # database reachable
curl -s localhost:8000/api/freshness | jq      # data age + FRESH/STALE/UNKNOWN
curl -s localhost:8000/api/alerts | jq         # which alerts are firing
curl -s localhost:8000/metrics | grep -E "http_requests_total|freshness"
```

Every alert below links here; the incident documents in `docs/incidents/`
record exercised timelines with MTTD/MTTR.

---

## INC-001 — Billing stale (`BillingDataStale` / `BillingDataMissing`)

**Symptom:** freshness > 24h (or UNKNOWN).

1. Confirm the platform's view: `curl /api/freshness`.
2. Check the source: newest `_PARTITIONTIME` in the BigQuery export table
   (`bq query 'SELECT MAX(_PARTITIONTIME) FROM ...'`).
3. If GCP stopped exporting → Billing console → Billing export → re-enable;
   wait for the next daily job.
4. If the export is fine but the platform is behind → re-run ingestion
   (`python -m costlab.seed --force` in demo; the refresh job in real mode).
5. Verify: `/api/freshness` returns FRESH and the gauge advances.

Details: `docs/incidents/INC-001-billing-stale.md` (MTTD 24h, MTTR 3h).

## INC-002 — BigQuery failure (`GCPBillingError` / `BigQueryQuerySlowOrFailing`)

**Symptom:** `GCPBillingError` in logs; refresh job fails; freshness grows.

1. Read the wrapped error in the logs — it names the failure class
   (auth / quota / table-not-found / schema).
2. Auth: verify ADC (`gcloud auth application-default login`) or the WIF
   binding; the platform never uses key files.
3. Table/schema: `bq show --schema` the export table; align
   `GCP_BILLING_TABLE` and the provider mapping if GCP renamed columns.
4. Quota/location: check the BigQuery console for quota hits and that
   `GCP_BILLING_LOCATION` matches the dataset.
5. Verify: a manual provider load succeeds; the dry-run log line shows sane
   bytes; freshness recovers.

Details: `docs/incidents/INC-002-bigquery-failure.md` (MTTD immediate, MTTR 1.5h).

## INC-003 — API outage (`APIAvailabilityLow` / `/ready` 503)

**Symptom:** availability SLI below 99.5%, `/ready` fails, or the host is
unreachable.

1. `docker compose ps` — is the API container up/restarting?
2. `docker compose logs api --tail 100` — crash, OOM, or migration failure?
3. Restart: `docker compose up -d api` (entrypoint re-runs idempotent
   migrations + seed).
4. If OOM on the 8 GB host: free memory (close heavy processes), add compose
   memory limits, keep heavy builds off the demo machine.
5. Verify: `/health` + `/ready` ok; availability SLI recovers as requests
   succeed (probe `/health` a few times).

Details: `docs/incidents/INC-003-api-outage.md` (MTTD ~1m, MTTR 10m).

## INC-004 — Recommendation failure (`RecommendationPipelineFailing`)

**Symptom:** `POST /api/recommendations/run` 500s or success SLI < 99%.

1. Read the 500 traceback in the logs (request id correlates the lines).
2. Identify the failing rule and the offending row via
   `GET /api/utilization` (missing/odd metric shapes are the usual cause).
3. Harden the rule (treat every evidence field as nullable) + add a
   regression test with the offending shape.
4. Re-run `POST /run`; confirm `recommendation_runs_total{result="success"}`
   increments and rows are (re)generated.
5. Verify: success SLI back above 99%; no new failures on repeat runs.

Details: `docs/incidents/INC-004-recommendation-failure.md` (MTTD immediate,
MTTR ~40m).

## INC-005 — Forecast failure

**Symptom:** `GET /api/forecast` 500s, or
`forecast_runs_total{result="failure"}` grows.

1. Replay the request with the same filters; read the traceback.
2. Inspect the daily series for a bad value
   (`GET /api/cost?...&page_size=50`) — dirty data is the usual cause.
3. Clean via the validated ingestion path (never hand-edit the DB).
4. Verify: `/api/forecast` returns points with
   `forecast_runs_total{result="success"}` advancing.

Details: `docs/incidents/INC-005-forecast-failure.md` (MTTD immediate,
MTTR ~25m).

---

## Alert → incident map

| Alert | Incident doc | Default severity |
| --- | --- | --- |
| `BillingDataStale` / `BillingDataMissing` | INC-001 | warning / critical |
| `GCPBillingError` / `BigQueryQuerySlowOrFailing` | INC-002 | warning (escalates) |
| `APIAvailabilityLow` | INC-003 | critical |
| `RecommendationPipelineFailing` | INC-004 | warning |
| Forecast failure counters | INC-005 | low/warning |
