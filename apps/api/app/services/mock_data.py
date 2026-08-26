"""Deterministic mock data generator for Cloud Cost Lab.

Uses a fixed seed so data is reproducible across restarts and tests.
Simulates 3 months of GCP billing data across multiple services,
projects, and environments.
"""

import hashlib
import random
from datetime import date, timedelta
from typing import Optional

SEED = 42

PROJECTS = [
    {
        "project_id": "cloud-cost-lab-prod",
        "project_name": "Cloud Cost Lab Production",
        "environment": "production",
        "team": "platform",
        "owner": "rifky",
    },
    {
        "project_id": "cloud-cost-lab-staging",
        "project_name": "Cloud Cost Lab Staging",
        "environment": "staging",
        "team": "platform",
        "owner": "rifky",
    },
    {
        "project_id": "cloud-cost-lab-dev",
        "project_name": "Cloud Cost Lab Development",
        "environment": "development",
        "team": "platform",
        "owner": "rifky",
    },
]

SERVICES = [
    {"service_id": "compute-engine", "service_name": "Compute Engine", "category": "Compute"},
    {"service_id": "cloud-sql", "service_name": "Cloud SQL", "category": "Database"},
    {"service_id": "cloud-storage", "service_name": "Cloud Storage", "category": "Storage"},
    {"service_id": "artifact-registry", "service_name": "Artifact Registry", "category": "Storage"},
]

RESOURCES = [
    {
        "resource_id": "vm-prod-api-01",
        "resource_name": "prod-api-server-01",
        "resource_type": "e2-standard-4",
        "service_id": "compute-engine",
        "project_id": "cloud-cost-lab-prod",
        "region": "asia-southeast1",
        "zone": "asia-southeast1-a",
        "environment": "production",
        "status": "active",
        "owner": "rifky",
        "team": "platform",
        "application": "api",
    },
    {
        "resource_id": "vm-prod-api-02",
        "resource_name": "prod-api-server-02",
        "resource_type": "e2-standard-4",
        "service_id": "compute-engine",
        "project_id": "cloud-cost-lab-prod",
        "region": "asia-southeast1",
        "zone": "asia-southeast1-b",
        "environment": "production",
        "status": "active",
        "owner": "rifky",
        "team": "platform",
        "application": "api",
    },
    {
        "resource_id": "vm-dev-01",
        "resource_name": "dev-workstation-01",
        "resource_type": "e2-standard-2",
        "service_id": "compute-engine",
        "project_id": "cloud-cost-lab-dev",
        "region": "asia-southeast1",
        "zone": "asia-southeast1-a",
        "environment": "development",
        "status": "active",
        "owner": "rifky",
        "team": "platform",
        "application": "development",
    },
    {
        "resource_id": "vm-idle-01",
        "resource_name": "idle-test-server",
        "resource_type": "e2-medium",
        "service_id": "compute-engine",
        "project_id": "cloud-cost-lab-dev",
        "region": "asia-southeast1",
        "zone": "asia-southeast1-a",
        "environment": "development",
        "status": "active",
        "owner": "UNALLOCATED",
        "team": "UNALLOCATED",
        "application": "UNALLOCATED",
    },
    {
        "resource_id": "sql-prod-01",
        "resource_name": "prod-database",
        "resource_type": "db-custom-2-8192",
        "service_id": "cloud-sql",
        "project_id": "cloud-cost-lab-prod",
        "region": "asia-southeast1",
        "zone": "asia-southeast1-a",
        "environment": "production",
        "status": "active",
        "owner": "rifky",
        "team": "platform",
        "application": "api",
    },
    {
        "resource_id": "sql-staging-01",
        "resource_name": "staging-database",
        "resource_type": "db-custom-1-4096",
        "service_id": "cloud-sql",
        "project_id": "cloud-cost-lab-staging",
        "region": "asia-southeast1",
        "zone": "asia-southeast1-a",
        "environment": "staging",
        "status": "active",
        "owner": "rifky",
        "team": "platform",
        "application": "api",
    },
    {
        "resource_id": "gcs-prod-assets",
        "resource_name": "prod-assets-bucket",
        "resource_type": "standard",
        "service_id": "cloud-storage",
        "project_id": "cloud-cost-lab-prod",
        "region": "asia-southeast1",
        "zone": None,
        "environment": "production",
        "status": "active",
        "owner": "rifky",
        "team": "platform",
        "application": "web",
    },
    {
        "resource_id": "ar-prod-images",
        "resource_name": "prod-container-images",
        "resource_type": "docker",
        "service_id": "artifact-registry",
        "project_id": "cloud-cost-lab-prod",
        "region": "asia-southeast1",
        "zone": None,
        "environment": "production",
        "status": "active",
        "owner": "rifky",
        "team": "platform",
        "application": "cicd",
    },
]

# Base daily cost per resource (USD)
BASE_DAILY_COSTS: dict[str, float] = {
    "vm-prod-api-01": 3.20,
    "vm-prod-api-02": 3.20,
    "vm-dev-01": 1.60,
    "vm-idle-01": 0.80,
    "sql-prod-01": 4.50,
    "sql-staging-01": 2.20,
    "gcs-prod-assets": 0.45,
    "ar-prod-images": 0.30,
}


def _deterministic_variation(resource_id: str, day: date, base_cost: float) -> float:
    """Generate a deterministic daily cost variation using a hash-based seed."""
    key = f"{resource_id}:{day.isoformat()}:{SEED}"
    hash_val = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    rng = random.Random(hash_val)
    variation = rng.uniform(-0.12, 0.15)
    return round(base_cost * (1 + variation), 4)


def _apply_growth(base_cost: float, day: date, reference_date: date) -> float:
    """Apply a month-over-month growth factor to simulate cost increases."""
    months_diff = (day.year - reference_date.year) * 12 + (day.month - reference_date.month)
    growth_factor = 1.0 + (months_diff * 0.08)
    return base_cost * max(growth_factor, 1.0)


def _inject_spike(resource_id: str, day: date) -> float:
    """Inject a cost spike for specific dates to simulate anomalies."""
    # Simulate a spike on the 15th of current month for compute
    if resource_id == "vm-prod-api-01" and day.day == 15 and day.month == 8:
        return 3.5
    return 1.0


def generate_cost_records(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict]:
    """Generate deterministic cost records for the given date range."""
    if end_date is None:
        end_date = date(2026, 8, 26)
    if start_date is None:
        start_date = end_date - timedelta(days=89)

    reference_date = start_date
    records = []

    current_day = start_date
    while current_day <= end_date:
        for resource in RESOURCES:
            rid = resource["resource_id"]
            base = BASE_DAILY_COSTS[rid]
            grown_base = _apply_growth(base, current_day, reference_date)
            daily_cost = _deterministic_variation(rid, current_day, grown_base)
            spike = _inject_spike(rid, current_day)
            final_cost = round(daily_cost * spike, 4)

            credits = 0.0
            if resource["environment"] == "development":
                credits = round(final_cost * 0.05, 4)

            records.append({
                "project_id": resource["project_id"],
                "project_name": next(
                    p["project_name"] for p in PROJECTS if p["project_id"] == resource["project_id"]
                ),
                "service_id": resource["service_id"],
                "service_name": next(
                    s["service_name"] for s in SERVICES if s["service_id"] == resource["service_id"]
                ),
                "sku": f"{resource['service_id']}/{resource['resource_type']}",
                "region": resource["region"],
                "resource_id": rid,
                "usage_date": current_day,
                "usage_amount": 24.0,
                "usage_unit": "hours",
                "cost": final_cost,
                "currency": "USD",
                "credits": credits,
                "net_cost": round(final_cost - credits, 4),
                "environment": resource["environment"],
                "team": resource["team"],
                "application": resource["application"],
            })
        current_day += timedelta(days=1)

    return records
