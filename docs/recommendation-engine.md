# Recommendation Engine — Cloud Cost Lab

## Overview

The recommendation engine evaluates resources against pluggable rules and generates evidence-based optimization recommendations. **No automatic infrastructure changes are made** — all recommendations require human approval.

## Architecture

```
Resources + Metrics
        ↓
  Recommendation Rules (evaluate)
        ↓
  Generate Recommendations
        ↓
  Priority Scoring
        ↓
  Human Review
        ↓
  Manual Approval
        ↓
  (Manual Implementation)
```

## Rule Interface

Every rule implements the `RecommendationRule` interface:

| Method | Returns | Purpose |
|--------|---------|---------|
| `evaluate(resource, metrics)` | bool | Does this rule apply? |
| `explain(resource, metrics)` | dict | What's wrong and what to do (title, problem, evidence, recommendation) |
| `calculate_saving(resource, metrics)` | float | Potential monthly savings (USD) |
| `calculate_risk(resource, metrics)` | str | LOW / MEDIUM / HIGH |
| `confidence(resource, metrics)` | str | HIGH / MEDIUM / LOW |
| `effort(resource, metrics)` | str | LOW / MEDIUM / HIGH (default: LOW) |
| `priority_score(resource, metrics)` | int | 0-100 (higher = more urgent) |

## Implemented Rules

### 1. IdleComputeRule

**Detects:** Compute resources with < 5% CPU utilization

**Evidence:**
- CPU avg < 5.0% over 30 days
- Resource is running but barely used

**Recommendation:** Schedule (start/stop on demand) or decommission

**Savings:** 90% of monthly cost

**Risk:**
- MEDIUM for production
- LOW for dev/staging

**Confidence:**
- HIGH if CPU < 2%
- MEDIUM if 2% ≤ CPU < 5%

### 2. OversizedComputeRule

**Detects:** Compute resources with CPU < 20% AND memory < 40%

**Evidence:**
- Both CPU and memory consistently underutilized
- Instance is larger than needed

**Recommendation:** Downsize to smaller instance type

**Savings:** 40% of monthly cost

**Risk:**
- LOW if CPU < 10%
- MEDIUM if 10% ≤ CPU < 20%

**Confidence:**
- HIGH if CPU < 15% AND memory < 30%
- MEDIUM if CPU < 20% AND memory < 40%

**Effort:** MEDIUM (requires migration)

### 3. UnusedDiskRule

**Detects:** Unattached disks OR disk utilization < 10%

**Evidence:**
- Status = "unattached" (no VM using this disk)
- OR disk utilization < 10% over 30 days

**Recommendation:**
- Unattached: review if data needed, snapshot then delete
- Low utilization: consolidate or resize

**Savings:**
- 100% for unattached disks
- 50% for underutilized disks

**Risk:**
- LOW for unattached
- MEDIUM for low utilization

**Confidence:**
- HIGH for unattached
- MEDIUM for low utilization

### 4. StorageRetentionRule

**Detects:** Storage/Artifact Registry with cost > $1/month

**Evidence:**
- Storage growing without lifecycle policies
- No automatic cleanup

**Recommendation:** Implement lifecycle policies (cold storage, retention limits, auto-delete)

**Savings:** 30% of monthly cost

**Risk:** LOW

**Confidence:** MEDIUM

**Effort:** MEDIUM (requires policy design)

### 5. CostAnomalyRule

**Detects:** Resources with > 50% cost increase

**Evidence:**
- Cost rose significantly vs previous period
- Investigate workload changes, traffic spikes, misconfigurations

**Recommendation:** Review recent changes, check for workload increases or billing errors

**Savings:** $0 (detective rule, not optimization)

**Risk:** LOW

**Confidence:** HIGH

## Recommendation Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Deterministic hash (resource_id + rule_name) |
| title | string | Brief summary |
| resource_id | string | Target resource |
| resource_name | string | Human-readable name |
| service | string | GCP service |
| environment | string | production / staging / development |
| problem | string | What's wrong |
| evidence | string | Observed data supporting the recommendation |
| recommendation | string | What action to take |
| current_cost | float | Monthly cost before optimization |
| potential_cost | float | Estimated monthly cost after optimization |
| potential_savings | float | Estimated monthly savings (USD) |
| savings_percentage | float | Savings as percentage of current cost |
| risk | string | LOW / MEDIUM / HIGH |
| confidence | string | HIGH / MEDIUM / LOW |
| effort | string | LOW / MEDIUM / HIGH |
| priority | int | 0-100 (higher = more urgent) |
| status | string | OPEN / APPROVED / REJECTED / IMPLEMENTED / VERIFIED |
| approval_required | bool | Always true (no auto-execution) |

## Priority Scoring

Default formula balances savings against risk:

```
base_score = min(saving * 2, 50)
confidence_bonus = {HIGH: 30, MEDIUM: 15, LOW: 0}
risk_penalty = {LOW: 0, MEDIUM: 20, HIGH: 40}

priority = base_score + confidence_bonus - risk_penalty
priority = clamp(priority, 0, 100)
```

High-saving, high-confidence, low-risk recommendations score highest.

## API Endpoints

### GET /api/recommendations

List all recommendations sorted by priority (descending).

**Response:**
```json
{
  "recommendations": [...],
  "total": 5
}
```

### GET /api/recommendations/{id}

Get detailed recommendation by ID.

**404** if not found.

## Frontend

### /recommendations — Recommendations Page

**Summary Card:**
- Total potential savings
- Active recommendation count

**Controls:**
- Sort by: Priority (default) or Potential Savings

**Recommendation Cards:**
- Title + resource info (name, service, environment)
- Savings amount + percentage
- Problem statement
- Evidence
- Recommendation action
- Risk, confidence, effort, priority badges
- ⚠ Approval Required indicator

## Design Decisions

### Evidence-Based Only

All savings calculations are based on observed metrics:
- Idle compute: 90% saving because resource is barely used
- Oversized: 40% saving based on typical rightsizing ratios
- Unused disk: 100% (unattached) or 50% (underutilized)
- Storage retention: 30% based on lifecycle policy impact
- Cost anomaly: $0 (detective, not optimization)

No guesses. Every recommendation explains **WHY** with observed data.

### No Automatic Actions

`approval_required = true` for all recommendations.

The system:
- ✓ Detects issues
- ✓ Calculates potential savings
- ✓ Prioritizes recommendations
- ✗ Does NOT modify infrastructure
- ✗ Does NOT auto-delete resources
- ✗ Does NOT auto-resize instances

Engineers review evidence and decide.

### Pluggable Rules

New rules are added by:
1. Create class extending `RecommendationRule`
2. Implement interface methods
3. Add to `ALL_RULES` list

No database changes needed — rules are code.

### Boundary Condition Testing

Tests cover:
- CPU: 0%, 2%, 4.9%, 5%, 10%, 20%
- Memory: 10%, 30%, 39%, 40%
- Null values
- Storage vs compute
- Production vs development
- Edge cases (exactly at threshold)

Prevents false positives.

## Lifecycle (Future)

Current: all recommendations are **OPEN**.

Future phases will implement:
- **APPROVED**: human approved, ready to implement
- **REJECTED**: human rejected, not actionable
- **IMPLEMENTED**: action taken
- **VERIFIED**: savings confirmed with post-change data

## Testing

121 backend tests passing, including:
- Boundary conditions (0, 5, 10, 20, null)
- Risk assessment (production vs dev)
- Confidence thresholds
- Service filtering (compute vs storage)
- Savings calculations
- Priority scoring
- API endpoints (list, detail, 404)
