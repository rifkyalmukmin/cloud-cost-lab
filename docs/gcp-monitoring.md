# GCP Monitoring Integration — Cloud Cost Lab

## Overview

Cloud Cost Lab integrates with GCP Cloud Monitoring to correlate cost data with real-time utilization and performance metrics. This enables evidence-based recommendations where cost + utilization + performance data are combined.

## Architecture

```
GCP Cloud Monitoring
        ↓
  Monitoring API (monitoring_v3)
        ↓
  GCPMonitoringProvider
        ↓
  MonitoringService (enrichment)
        ↓
  Recommendations (evidence)
```

## Provider Abstraction

```python
class MonitoringDataProvider(ABC):
    def get_resource_metrics(resource_id, start, end) -> Optional[dict]
    def get_all_resource_metrics(start, end) -> list[dict]
    def get_data_freshness() -> MetricsFreshness
    def is_available() -> bool

# Implementations
MockMonitoringProvider   # default, no GCP needed
GCPMonitoringProvider    # requires GCP monitoring access
```

## Metrics Collected

| Metric | Source | Compute | SQL | Storage |
|--------|--------|---------|-----|---------|
| CPU utilization | compute.googleapis.com | YES | YES | NO |
| Memory utilization | agent.googleapis.com | YES | YES | NO |
| Disk utilization | compute.googleapis.com | YES | YES | YES |
| Network in | compute.googleapis.com | YES | YES | YES |
| Network out | compute.googleapis.com | YES | YES | YES |
| Connections | cloudsql.googleapis.com | NO | YES | NO |
| Request count | custom / LB metrics | YES | YES | YES |
| Latency | custom / LB metrics | YES | YES | YES |

## Evidence Strength

The system assesses how strong the monitoring evidence is for each resource:

| Strength | Criteria |
|----------|----------|
| **STRONG** | ≥14 days observation + ≥2 metrics available |
| **MODERATE** | ≥7 days observation + ≥1 metric available |
| **WEAK** | ≥3 days observation or few metrics |
| **INSUFFICIENT** | <3 days observation |

Recommendations only trigger when evidence is at least MODERATE.

## Enriched Recommendation Evidence

Example of monitoring-enriched recommendation:

```
Title: Idle compute resource detected
Resource: idle-test-server
Monthly Cost: $24.00
CPU Average: 3% (over 30 days)
Memory Average: 12%
Request Count: 0 requests/day
Connections: 0
Observation: 30 days
Evidence Strength: STRONG

Problem: Resource is running but barely utilized
Saving: $21.60/month (90%)
Confidence: HIGH (30-day observation, 0 requests)
```

vs. recommendation without monitoring:

```
Title: Idle compute resource detected
CPU Average: 3%
Evidence Strength: WEAK (no request/connection data)
Confidence: MEDIUM
```

## API Endpoints

### GET /api/monitoring

Get all resource metrics enriched with cost and evidence strength.

**Response:**
```json
{
  "period_start": "2026-07-28",
  "period_end": "2026-08-26",
  "monitoring_freshness": {
    "last_updated": "2026-08-26T11:55:00",
    "data_age_hours": 0.1,
    "status": "FRESH"
  },
  "resources": [
    {
      "resource_id": "vm-prod-api-01",
      "resource_name": "prod-api-server-01",
      "service": "Compute Engine",
      "environment": "production",
      "monthly_cost": 96.0,
      "metrics": {
        "cpu_avg": 62.0,
        "memory_avg": 71.0,
        "disk_avg": 45.0,
        "network_in_avg_mb": 100.0,
        "network_out_avg_mb": 60.0,
        "connections_avg": 120.0,
        "request_count_daily_avg": 45000.0,
        "latency_avg_ms": 85.0
      },
      "observation_days": 30,
      "evidence_strength": "STRONG"
    }
  ]
}
```

### GET /api/monitoring/{resource_id}

Get detailed metrics with time series for a specific resource.

**Response includes:**
- Summary metrics (cpu_avg, memory_avg)
- Time series data (30-day daily)
- Evidence strength
- Cost data

## GCP Setup

### Permissions Required

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:cost-lab-reader@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.viewer"
```

| Role | Purpose |
|------|---------|
| monitoring.viewer | Read metric data |

### Install Dependencies

```bash
pip install google-cloud-monitoring
```

## Data Freshness

Cloud Monitoring provides near-real-time data (~1 minute lag).

| Status | Condition |
|--------|-----------|
| **FRESH** | Provider accessible, data flowing |
| **STALE** | Provider accessible, data gap detected |
| **UNKNOWN** | Provider not accessible |

## Cost of Monitoring Queries

Cloud Monitoring API:
- Free tier: 150M API calls/month
- Typical Cloud Cost Lab usage: ~1000 calls/day = negligible cost

No BigQuery charges for monitoring queries (uses Monitoring API directly).

## Destroy / Disable

```bash
# Switch to demo mode
DEMO_MODE=true

# Or remove monitoring permission only
gcloud projects remove-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:cost-lab-reader@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.viewer"
```

## Design Decisions

### Evidence Strength as First-Class Concept

The system explicitly grades how strong the evidence is rather than treating all data equally. A recommendation based on 30 days of CPU + memory + request data is far more reliable than one based on 3 days of CPU alone.

### Metrics Don't Directly Create Recommendations

Monitoring data enriches and strengthens recommendations — it doesn't generate them alone. The recommendation rules (Phase 5) use metrics as input but also require:
- Cost data (from billing provider)
- Duration (observation_days)
- Pattern stability

This prevents false positives from transient metric spikes.

### Provider Failure Graceful Degradation

If the GCP monitoring provider fails:
- System falls back to cost-only recommendations
- Evidence strength is marked WEAK or INSUFFICIENT
- User is informed via freshness status
- No crash, no data loss
