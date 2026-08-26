# Runbook: API Outage

## Alert
APIHighErrorRate (CRITICAL) / Health check failure

## Quick Check (< 1 minute)

```bash
# Health check
curl -s http://localhost:8000/health || echo "UNREACHABLE"

# Container status
docker ps | grep cloud-cost-lab

# Recent logs
docker logs cloud-cost-lab-api --tail 50
```

## Immediate Mitigation (< 2 minutes)

```bash
# Restart the container
docker compose restart api

# Verify recovery
sleep 5 && curl http://localhost:8000/health
```

## Diagnosis

### 1. Is it a crash?
```bash
docker logs cloud-cost-lab-api 2>&1 | grep -i "error\|traceback\|exception" | tail -20
```

### 2. Is it OOM?
```bash
docker stats cloud-cost-lab-api --no-stream
# Check memory usage vs limit
```

### 3. Is it a dependency?
```bash
# Check if database is reachable (if using PostgreSQL)
docker exec cloud-cost-lab-api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/ready').read())"
```

### 4. Was there a recent deployment?
```bash
git log --oneline -5
docker inspect cloud-cost-lab-api | grep Created
```

## Resolution

### If crash loop:
1. Check logs for root cause
2. If config error: fix .env and restart
3. If code bug: rollback to previous commit
   ```bash
   git log --oneline -5
   git revert HEAD
   docker compose build api && docker compose up -d api
   ```

### If OOM:
1. Increase container memory limit in docker-compose.yml
2. Investigate memory leak in application

### If dependency failure:
1. Check provider availability (BigQuery, Monitoring)
2. Set DEMO_MODE=true as immediate mitigation
3. Fix provider issue separately

## Post-Incident
1. Document timeline in incident template
2. Calculate MTTD and MTTR
3. Implement prevention measure
4. Update monitoring if detection was slow
