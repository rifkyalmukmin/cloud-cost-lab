# Runbook: Recommendation Engine Failure

## Alert
RecommendationFailure (WARNING)

## Quick Check (< 2 minutes)

```bash
# Test recommendation endpoint
curl http://localhost:8000/api/recommendations

# Check logs
docker logs cloud-cost-lab-api 2>&1 | grep -i "recommend" | tail -20

# Check metrics
curl http://localhost:8000/api/observability/metrics | python3 -m json.tool | grep -i recommend
```

## Diagnosis

### 1. Which rule failed?
Check logs for the specific rule class name that threw an error.

### 2. Which resource caused it?
Check logs for the resource_id that triggered the failure.

### 3. Is it a data issue?
```bash
# Check utilization data
curl http://localhost:8000/api/utilization

# Check if specific resource has valid data
curl http://localhost:8000/api/monitoring/RESOURCE_ID
```

## Resolution

### If rule bug (null handling):
1. Identify the failing rule in logs
2. Add null check for the edge case
3. Add test case for the specific input
4. Deploy fix

### If data unavailable:
1. Check monitoring provider: `curl /api/monitoring`
2. If provider down: recommendations still work with available data
3. Rules should handle None gracefully — if not, fix the rule

### Immediate mitigation:
Recommendations endpoint still returns results from rules that succeed.
Only the failing rule's recommendations will be missing.

## Prevention
- All rules must handle None/0/missing data without crashing
- Boundary condition tests (CPU: 0, null; Memory: null, 0)
- Each rule evaluation is independent (one failure doesn't break others)
