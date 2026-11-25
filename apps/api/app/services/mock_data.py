"""Deterministic mock data generator for Cloud Cost Lab.

Uses a fixed seed so data is reproducible across restarts and tests.
Simulates 3 months of GCP billing data across multiple services,
projects, and environments.
"""

import hashlib
import random
from datetime import date, timedelta
from typing import Any, Optional, TypedDict

from app.clock import reference_today

SEED = 42


class ResourceSeed(TypedDict):
    resource_id: str
    resource_name: str
    resource_type: str
    service_id: str
    project_id: str
    region: str
    zone: str | None
    environment: str
    status: str
    owner: str
    team: str
    application: str

PROJECTS: list[dict[str, str]] = [
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

SERVICES: list[dict[str, str]] = [
    {"service_id": "compute-engine", "service_name": "Compute Engine", "category": "Compute"},
    {"service_id": "cloud-sql", "service_name": "Cloud SQL", "category": "Database"},
    {"service_id": "cloud-storage", "service_name": "Cloud Storage", "category": "Storage"},
    {"service_id": "artifact-registry", "service_name": "Artifact Registry", "category": "Storage"},
]

RESOURCES: list[ResourceSeed] = [
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


RESOURCE_UTILIZATION: dict[str, dict[str, float | None]] = {
    "vm-prod-api-01": {"cpu_avg": 62.0, "memory_avg": 71.0, "disk_avg": 45.0},
    "vm-prod-api-02": {"cpu_avg": 58.0, "memory_avg": 68.0, "disk_avg": 42.0},
    "vm-dev-01": {"cpu_avg": 25.0, "memory_avg": 35.0, "disk_avg": 30.0},
    "vm-idle-01": {"cpu_avg": 3.0, "memory_avg": 12.0, "disk_avg": 8.0},
    "sql-prod-01": {"cpu_avg": 45.0, "memory_avg": 60.0, "disk_avg": 55.0},
    "sql-staging-01": {"cpu_avg": 15.0, "memory_avg": 28.0, "disk_avg": 20.0},
    "gcs-prod-assets": {"cpu_avg": None, "memory_avg": None, "disk_avg": 62.0},
    "ar-prod-images": {"cpu_avg": None, "memory_avg": None, "disk_avg": 38.0},
}

RESOURCE_LABELS: dict[str, dict[str, str]] = {
    "vm-prod-api-01": {"env": "production", "service": "api", "managed-by": "terraform"},
    "vm-prod-api-02": {"env": "production", "service": "api", "managed-by": "terraform"},
    "vm-dev-01": {"env": "development", "purpose": "workstation"},
    "vm-idle-01": {},
    "sql-prod-01": {"env": "production", "service": "api", "ha": "true"},
    "sql-staging-01": {"env": "staging", "service": "api"},
    "gcs-prod-assets": {"env": "production", "type": "assets"},
    "ar-prod-images": {"env": "production", "type": "docker"},
}

POTENTIAL_SAVINGS: dict[str, float] = {
    "vm-prod-api-01": 0.0,
    "vm-prod-api-02": 0.0,
    "vm-dev-01": 12.0,
    "vm-idle-01": 24.0,
    "sql-prod-01": 0.0,
    "sql-staging-01": 18.0,
    "gcs-prod-assets": 2.0,
    "ar-prod-images": 4.0,
}


def generate_utilization_records(
    resource_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Generate deterministic utilization records for a resource."""
    if end_date is None:
        end_date = reference_today()
    if start_date is None:
        start_date = end_date - timedelta(days=29)

    base_util = RESOURCE_UTILIZATION.get(resource_id)
    if not base_util:
        return []

    records = []
    current_day = start_date
    while current_day <= end_date:
        key = f"util:{resource_id}:{current_day.isoformat()}:{SEED}"
        hash_val = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
        rng = random.Random(hash_val)

        cpu = None
        memory = None
        if base_util["cpu_avg"] is not None:
            cpu = round(base_util["cpu_avg"] * rng.uniform(0.7, 1.3), 1)
            cpu = min(cpu, 100.0)
        if base_util["memory_avg"] is not None:
            memory = round(base_util["memory_avg"] * rng.uniform(0.8, 1.2), 1)
            memory = min(memory, 100.0)

        disk = None
        if base_util["disk_avg"] is not None:
            disk = round(base_util["disk_avg"] * rng.uniform(0.9, 1.1), 1)
            disk = min(disk, 100.0)

        records.append({
            "resource_id": resource_id,
            "date": current_day.isoformat(),
            "cpu_utilization": cpu,
            "memory_utilization": memory,
            "disk_utilization": disk,
            "network_in_mb": round(rng.uniform(10, 500), 1) if cpu else round(rng.uniform(1, 50), 1),
            "network_out_mb": round(rng.uniform(5, 300), 1) if cpu else round(rng.uniform(0.5, 20), 1),
        })
        current_day += timedelta(days=1)

    return records


def generate_cost_records(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Generate deterministic cost records for the given date range."""
    if end_date is None:
        end_date = reference_today()
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
