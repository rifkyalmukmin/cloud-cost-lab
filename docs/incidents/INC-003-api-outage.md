# INC-003 — API outage

| | |
| --- | --- |
| Severity | CRITICAL |
| Detection | Alert `APIAvailabilityLow` (`job:api_availability:ratio_rate5m < 0.995`); `/ready` fails; external probe of `/health` |
| Impact | Dashboard shows error states (graceful degradation); no data corruption risk — the API is read-only for consumers |

## Timeline (scenario exercise — simulated by stopping the API container)

1. T+0 — API container stopped (`docker compose stop api`).
2. T+1m — external uptime probe fails; **MTTD ~1m** (in-process availability SLI cannot observe its own death — an external probe or the container orchestrator's restart policy is the compensating control).
3. T+2m — runbook: `docker compose ps` shows unhealthy; inspect `docker compose logs api`.
4. T+8m — root cause in the exercise: OOM on the 8 GB laptop during a parallel heavy build; memory pressure killed the container.
5. T+10m — `docker compose up -d api` restores service (migrations/seed idempotent). **MTTR 10m**.

## Root cause
Local resource exhaustion (single-host demo limitation). In a real deployment the fix is a restart policy + resource limits + multiple replicas.

## Resolution & prevention
- Resolution: restart; verify `/health`, `/ready`, and availability SLI recovery.
- Prevention: container memory limits sized to the laptop; restart policy `unless-stopped` (already in compose); keep heavy builds off the demo host.
