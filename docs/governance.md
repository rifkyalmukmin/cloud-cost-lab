# Governance Policies — Cloud Cost Lab

## Overview

Governance policies enforce organizational standards for resource management. Policies generate **warnings and recommendations only** — no automatic destructive actions are taken.

## Policy Status Levels

| Status | Description |
|--------|-------------|
| **PASS** | Resource complies with policy |
| **WARNING** | Resource triggers policy warning (soft violation) |
| **VIOLATION** | Resource violates policy (hard violation) |

## Implemented Policies

### 1. REQUIRE_OWNER_LABEL

**Description:** All resources must have a clearly defined owner

**Triggers VIOLATION when:**
- Resource has no owner field
- Owner is "UNALLOCATED"

**Recommendation:** "Assign an owner to enable accountability and cost allocation"

### 2. REQUIRE_ENVIRONMENT_LABEL

**Description:** All resources must be tagged with an environment

**Triggers VIOLATION when:**
- Resource has no environment label
- Environment is not one of: production, staging, development

**Recommendation:** "Tag resource with environment: production, staging, or development"

### 3. MAX_MONTHLY_COST

**Description:** Development resources must not exceed $100/month per resource

**Triggers VIOLATION when:**
- Development resource cost > $100/month

**Triggers WARNING when:**
- Staging resource cost > $200/month

**Recommendation:**
- VIOLATION: "Downsize resource or review if it should be in development environment"
- WARNING: "Review if resource sizing is appropriate for staging workload"

### 4. NO_PUBLIC_DATABASE

**Description:** Databases should not be publicly accessible

**Triggers VIOLATION when:**
- Resource is a database (SQL/database in service name)
- Resource has `public_access = true`

**Recommendation:** "Restrict database access to private network only"

### 5. DEV_RESOURCE_SCHEDULE

**Description:** Development compute resources should use scheduling to reduce costs

**Triggers WARNING when:**
- Resource environment = development
- Resource service contains "compute"
- Resource is not scheduled

**Recommendation:** "Implement start/stop schedule (e.g., business hours only) to save ~60% on compute costs"

## API Endpoint

### GET /api/policies

Evaluate all policies against all resources.

**Response:**
```json
{
  "summary": {
    "total_resources": 8,
    "total_policies": 5,
    "violations": 2,
    "warnings": 3,
    "passed": 35
  },
  "policies": [
    {
      "name": "REQUIRE_OWNER_LABEL",
      "description": "All resources must have a clearly defined owner"
    }
  ],
  "results": [
    {
      "resource_id": "vm-idle-01",
      "resource_name": "idle-test-server",
      "service": "Compute Engine",
      "environment": "development",
      "policy_results": [
        {
          "policy": "REQUIRE_OWNER_LABEL",
          "status": "VIOLATION",
          "message": "Resource 'idle-test-server' has no owner assigned",
          "recommendation": "Assign an owner to enable accountability and cost allocation"
        }
      ]
    }
  ]
}
```

## Policy Interface

All policies implement the `Policy` interface:

```python
class Policy(ABC):
    def name(self) -> str: ...
    def description(self) -> str: ...
    def evaluate(self, resource: dict) -> dict: ...
```

New policies are added by:
1. Create class extending `Policy`
2. Implement interface methods
3. Add to `ALL_POLICIES` list

## Design Decisions

### Warnings Only

Policies generate audit information:
- Status (PASS/WARNING/VIOLATION)
- Message (what's wrong)
- Recommendation (what to do)

They do NOT:
- Delete resources
- Modify resource configuration
- Stop resource creation
- Block deployments

Engineers review violations and take appropriate action.

### Pluggable Architecture

Policies are code, not configuration. This allows:
- Complex evaluation logic
- Strong typing
- Unit testing
- Version control
- Code review

### No False Positives

Policy evaluation is based on observed resource attributes:
- owner field
- environment label
- monthly cost
- service type
- scheduling status

No guessing or inference — only hard data.

## Testing

41 new tests covering:
- All policy types
- PASS/WARNING/VIOLATION conditions
- Boundary conditions (cost thresholds)
- Edge cases (null, missing, invalid values)
- API integration
