# INC-004 — Recommendation failure

| | |
| --- | --- |
| Severity | WARNING |
| Detection | Alert `RecommendationPipelineFailing` (`recommendation_runs_total{result="failure"}` pushes success below 99%); `POST /api/recommendations/run` returns 500 with request id |
| Impact | Recommendations stop updating; existing rows remain available (last-known-good state) |

## Timeline (scenario exercise — simulated by injecting a rule exception during a run)

1. T+0 — a rule raises mid-run (simulated: malformed utilization row reaching a rule that assumed non-null).
2. T+0 — `POST /run` returns 500; `recommendation_runs_total{result="failure"}` increments; **MTTD immediate** (in-process).
3. T+10m — runbook: read the traceback (request id in logs), identify the failing rule, inspect the offending row via the utilization endpoints.
4. T+40m — rule hardened (guards before assumptions); engine re-run succeeds. **MTTR ~40m**.
5. T+45m — success SLI recovers above 99% over the rolling window.

## Root cause
A rule assumed a metric field was present; defensive guards were missing for an edge the mock dataset never exercised.

## Resolution & prevention
- Resolution: rule guards + regression test with the offending shape (the Phase 5 suite already pins CPU-null and boundary behaviour — extended).
- Prevention: rules must treat every evidence field as nullable; the engine wraps runs and counts failures (implemented); failure counter + success SLI (implemented).
