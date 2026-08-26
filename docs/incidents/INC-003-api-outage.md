# INC-003: API Outage

## Severity
CRITICAL

## Detection
- SLI: api_availability drops below 99.5%
- Metric: http_requests_total with status=5xx
- Health check: /health returns non-200
- MTTD target: < 1 minute (health check interval)

## Impact
- Dashboard unavailable
- No cost data accessible
- No recommendations visible
- Budget alerts not displayed
- Users cannot access the platform

## Timeline (Template)
| Time | Event |
|------|-------|
| T+0m | API starts returning 5xx errors |
| T+1m | Health check fails |
| T+1m | Alert fires: APIHighErrorRate |
| T+Xm | Engineer investigates |
| T+Xm | Root cause identified |
| T+Xm | Service restored |

## Root Cause Categories
1. Application crash (unhandled exception)
2. Out of memory
3. Database connection failure
4. Dependency unavailable (BigQuery, Monitoring)
5. Configuration error after deployment
6. Container crash loop
7. Resource exhaustion (CPU, disk)

## Resolution Steps
1. Check /health endpoint — is it responding?
2. Check application logs for crash/exception
3. Check container status: `docker ps` or Cloud Run console
4. Check resource usage (CPU, memory)
5. If crash: check recent deployment, rollback if needed
6. If OOM: increase memory limit or fix memory leak
7. If dependency: check BigQuery/Monitoring provider availability
8. Restart service: `docker compose restart api`

## MTTD
Target: < 1 minute
Health check runs every 30 seconds.

## MTTR
Target: < 15 minutes
- Restart fixes most issues: < 2 minutes
- Rollback: < 5 minutes
- Config fix: < 15 minutes

## Prevention
- Health checks in Docker and orchestrator
- Graceful error handling (global exception handler)
- Resource limits configured
- Structured logging for fast diagnosis
- Automated restart on failure (Docker restart policy)

## Runbook
See: docs/runbooks/api-outage.md
