# Resource Inventory — Cloud Cost Lab

## Overview

The resource inventory tracks all cloud resources with their associated cost, utilization, and ownership data. It links cost to specific resources so engineers can identify which resources drive spend.

## Data Model

### Resource Fields

| Field | Type | Description |
|-------|------|-------------|
| resource_id | string | Unique identifier |
| name | string | Human-readable name |
| type | string | Instance type / SKU (e.g., e2-standard-4) |
| project | string | GCP project ID |
| service | string | GCP service (Compute Engine, Cloud SQL, etc.) |
| region | string | GCP region |
| zone | string | GCP zone (null for regional resources) |
| environment | string | production / staging / development |
| status | string | active / stopped / terminated |
| owner | string | Resource owner (UNALLOCATED if unknown) |
| team | string | Owning team (UNALLOCATED if unknown) |
| application | string | Application label (UNALLOCATED if unknown) |
| labels | object | Key-value labels/tags |
| created_at | date | Resource creation date |
| last_seen | date | Last time resource was observed |

### Utilization Metrics

| Metric | Type | Description |
|--------|------|-------------|
| cpu_utilization | float | CPU usage percentage (null for storage) |
| memory_utilization | float | Memory usage percentage (null for storage) |
| disk_utilization | float | Disk usage percentage |
| network_in_mb | float | Inbound network MB |
| network_out_mb | float | Outbound network MB |

### Cost Linkage

Each resource has:
- **monthly_cost**: estimated from base daily cost × 30
- **potential_saving**: estimated saving if optimized
- **cost_history**: daily cost for the current month

## API Endpoints

### GET /api/resources

List all resources with filtering and pagination.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| project | string | Filter by project ID |
| service | string | Filter by service ID |
| region | string | Filter by region |
| environment | string | Filter by environment |
| status | string | Filter by status |
| owner | string | Filter by owner |
| team | string | Filter by team |
| page | int | Page number (default: 1, min: 1) |
| page_size | int | Items per page (default: 20, max: 100) |

**Response:**
```json
{
  "data": [...],
  "total": 8,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### GET /api/resources/{resource_id}

Get detailed resource information.

**Response includes:**
- All resource metadata
- Labels
- Monthly cost (actual, calculated from records)
- Potential saving
- Utilization summary (cpu_avg, memory_avg, disk_avg)
- Utilization history (30-day daily records)
- Cost history (current month daily records)

**404** if resource not found.

## Frontend

### /resources — Resource List

Table view with columns:
- Resource (name + service)
- Type
- Project
- Region
- Environment
- Status (badge)
- Monthly Cost
- CPU (progress bar)
- Memory (progress bar)
- Potential Saving

Features:
- Environment filter dropdown
- Pagination controls
- Click-through to detail view

### /resources/[id] — Resource Detail

Shows:
- Summary cards (monthly cost, potential saving, CPU avg, memory avg)
- Cost history chart (area chart, current month)
- CPU utilization chart (area chart, 30-day)
- Metadata table (resource ID, type, service, project, region, zone, status, dates)
- Ownership table (environment, owner, team, application, labels)

## UNALLOCATED Resources

Resources without clear ownership display `UNALLOCATED` for owner, team, and application fields. This is intentional — we never guess ownership. Missing labels are highlighted in the detail view.

## Mock Data (8 Resources)

| Resource | Service | Environment | CPU Avg | Saving |
|----------|---------|-------------|---------|--------|
| prod-api-server-01 | Compute Engine | production | 62% | $0 |
| prod-api-server-02 | Compute Engine | production | 58% | $0 |
| dev-workstation-01 | Compute Engine | development | 25% | $12 |
| idle-test-server | Compute Engine | development | 3% | $24 |
| prod-database | Cloud SQL | production | 45% | $0 |
| staging-database | Cloud SQL | staging | 15% | $18 |
| prod-assets-bucket | Cloud Storage | production | N/A | $2 |
| prod-container-images | Artifact Registry | production | N/A | $4 |

## Design Decisions

- Utilization bars use traffic-light colors: green (< 50%), amber (50-80%), red (> 80%)
- Storage resources show N/A for CPU/memory (they don't have compute metrics)
- Potential savings are pre-calculated heuristics (real savings come from Phase 4 recommendations)
- Pagination enforced (max 100 per page) to prevent unbounded responses
