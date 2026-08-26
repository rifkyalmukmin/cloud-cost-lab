# Savings Verification — Cloud Cost Lab

## Overview

Cloud Cost Lab distinguishes between **potential savings** (estimated) and **realized savings** (verified with actual data). A recommendation is NOT considered "realized savings" until actual post-change cost data confirms the reduction.

## Lifecycle

```
OPEN → APPROVED → IMPLEMENTED → VERIFIED
         ↓
      REJECTED (at any stage before VERIFIED)
```

| Status | Meaning |
|--------|---------|
| **OPEN** | Recommendation generated, awaiting review |
| **APPROVED** | Human approved, ready for implementation |
| **REJECTED** | Human rejected with reason |
| **IMPLEMENTED** | Action taken, cost_before recorded |
| **VERIFIED** | Actual cost_after observed, realized_savings calculated |

## Savings Categories

### Potential Savings
- Estimated based on utilization analysis and rules
- No action taken yet
- Label: "Estimated savings if implemented"
- NOT realized — just a projection

### Approved Savings
- Human has approved the recommendation
- Still estimated (no implementation yet)
- Label: "Approved, awaiting implementation"

### Implemented Savings
- Action was taken (instance resized, resource deleted, etc.)
- cost_before recorded at implementation time
- Awaiting verification with actual post-change data
- Label: "Implemented, awaiting verification"
- Still NOT realized — need actual data

### Realized Savings (VERIFIED)
- Actual cost_after observed from billing data
- realized_savings = cost_before - cost_after
- Label: "Verified with actual before/after data"
- **This is the only category that counts as REALIZED**

## Before/After Calculation

```
cost_before = monthly cost at time of implementation
cost_after  = actual monthly cost observed after change
realized_savings = cost_before - cost_after
```

If cost_after > cost_before, realized_savings is negative (cost increased — failed optimization).

## API Endpoints

### GET /api/savings

Get savings summary across all stages.

**Response:**
```json
{
  "potential": {
    "count": 3,
    "total_savings": 42.50,
    "label": "Estimated savings if all open recommendations are implemented"
  },
  "approved": {
    "count": 1,
    "total_savings": 12.00,
    "label": "Approved, awaiting implementation"
  },
  "implemented": {
    "count": 1,
    "total_savings": 19.20,
    "label": "Implemented, awaiting verification with actual data"
  },
  "verified": {
    "count": 1,
    "total_savings": 21.60,
    "label": "Verified with actual before/after cost data (REALIZED)"
  },
  "rejected": {
    "count": 1
  },
  "total_realized_savings": 21.60,
  "total_potential_savings": 73.70
}
```

### POST /api/savings/{id}/approve
```json
{"actor": "rifky"}
```

### POST /api/savings/{id}/reject
```json
{"actor": "rifky", "reason": "Resource needed for load test"}
```

### POST /api/savings/{id}/implement
```json
{"actor": "rifky"}
```

### POST /api/savings/{id}/verify
```json
{"cost_after": 3.50}
```

### GET /api/savings/audit-log

Full audit trail of all lifecycle transitions.

**Response:**
```json
{
  "audit_log": [
    {
      "timestamp": "2026-08-26T12:00:00Z",
      "action": "APPROVED",
      "recommendation_id": "abc123",
      "actor": "rifky"
    },
    {
      "timestamp": "2026-08-26T12:00:00Z",
      "action": "VERIFIED",
      "recommendation_id": "abc123",
      "actor": "system",
      "cost_before": 24.0,
      "cost_after": 2.4,
      "realized_savings": 21.6
    }
  ]
}
```

## Audit Log

Every lifecycle transition is recorded:
- **Timestamp**: when the action occurred
- **Action**: APPROVED, REJECTED, IMPLEMENTED, VERIFIED
- **Actor**: who performed the action
- **Reason**: why (for rejections)
- **Cost data**: before/after (for verifications)

## Rules

### What counts as "Realized Savings"
- Status = VERIFIED
- cost_after observed from actual billing data
- realized_savings = cost_before - cost_after

### What does NOT count as "Realized Savings"
- Open recommendations (just estimates)
- Approved but not implemented
- Implemented but not verified
- Simulated savings

### Negative Savings
If cost_after > cost_before:
- realized_savings will be negative
- This indicates the optimization didn't work
- Still recorded for transparency

## Lifecycle Enforcement

| Current Status | Allowed Transitions |
|---------------|-------------------|
| OPEN | → APPROVED, → REJECTED |
| APPROVED | → IMPLEMENTED, → REJECTED |
| IMPLEMENTED | → VERIFIED, → REJECTED |
| VERIFIED | (terminal state) |
| REJECTED | (terminal state) |

Invalid transitions return HTTP 400 with explanation.

## Testing

25 tests covering:
- Full lifecycle (OPEN → APPROVED → IMPLEMENTED → VERIFIED)
- Rejection at various stages
- Invalid transitions (cannot approve non-OPEN, cannot implement non-APPROVED)
- Before/after cost calculation
- Nonexistent recommendation
- Audit log generation
- API endpoints (approve, reject, implement, verify)
- Summary calculation
- Label accuracy (potential vs realized)
