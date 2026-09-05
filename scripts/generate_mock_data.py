#!/usr/bin/env python3
"""Generate the deterministic Cloud Cost Lab mock dataset.

Writes data/mock/{projects,resources,cost,usage}.json.

Determinism rules (ADR-003):
- every value comes from fixed base rates, fixed multipliers and a fixed seed;
- regenerating the files must produce byte-identical output on any machine;
- never derive anything from the current wall clock.

The committed files are the source of truth for demos and tests; re-run this
script only when intentionally changing the dataset (review the diff first).

Stdlib only — this script must not import application code.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCK_DIR = REPO_ROOT / "data" / "mock"

DATE_START = date(2026, 6, 1)
DATE_END = date(2026, 9, 5)
END_TS = f"{DATE_END.isoformat()}T00:00:00Z"

# Monthly spend ramp: rising cost story (June base -> September elevated run-rate).
MONTH_MULTIPLIER = {6: 0.82, 7: 0.92, 8: 1.03, 9: 1.12}
# Scenario: unexpected Compute cost spike, one week in August (+35%).
SPIKE_START, SPIKE_END, SPIKE_FACTOR = date(2026, 8, 10), date(2026, 8, 16), 1.35
# Scenario: elevated September dev activity (budget-risk run-rate).
SEPT_DEV_BOOST_PROJECTS = {"cc-lab-shop-dev", "cc-lab-legacy-sandbox"}
SEPT_DEV_BOOST = 1.5
# Dev VMs are barely used on weekends.
WEEKEND_FACTOR = 0.35
COST_SEED, USAGE_SEED = 42, 43
PROD_CREDIT_RATE = 0.05  # simulated committed-use discount on production rows

PROJECTS: list[dict] = [
    {
        "project_id": "cc-lab-shop-prod",
        "display_name": "Shop Platform — Production",
        "environment": "production",
        "labels": {
            "environment": "production",
            "team": "platform",
            "application": "shop",
            "owner": "rifky",
        },
    },
    {
        "project_id": "cc-lab-shop-staging",
        "display_name": "Shop Platform — Staging",
        "environment": "staging",
        "labels": {
            "environment": "staging",
            "team": "platform",
            "application": "shop",
            "owner": "rifky",
        },
    },
    {
        "project_id": "cc-lab-shop-dev",
        "display_name": "Shop Platform — Development",
        "environment": "development",
        "labels": {
            "environment": "development",
            "team": "platform",
            "application": "shop",
            "owner": "rifky",
        },
    },
    # Deliberately unallocated: no team/owner/application labels (demo scenario 8).
    {
        "project_id": "cc-lab-legacy-sandbox",
        "display_name": "Legacy Sandbox",
        "environment": "development",
        "labels": {"environment": "development"},
    },
]

SERVICES: dict[str, dict[str, str]] = {
    "compute-engine": {"display_name": "Compute Engine", "category": "compute"},
    "cloud-sql": {"display_name": "Cloud SQL", "category": "database"},
    "cloud-storage": {"display_name": "Cloud Storage", "category": "storage"},
    "artifact-registry": {"display_name": "Artifact Registry", "category": "storage"},
}

# base_daily_cost in USD; usage profile per resource (see usage section below).
RESOURCES: list[dict] = [
    # --- Compute Engine ---
    {
        "resource_id": "vm-shop-api-prod-1",
        "resource_name": "shop-api-prod-1",
        "type": "vm_instance",
        "service_id": "compute-engine",
        "project_id": "cc-lab-shop-prod",
        "region": "us-central1",
        "zone": "us-central1-a",
        "status": "RUNNING",
        "machine_type": "e2-standard-2",
        "sku": "E2 instance core hours",
        "base_daily_cost": 0.26,
        "always_on": True,
    },
    {
        "resource_id": "vm-shop-api-prod-2",
        "resource_name": "shop-api-prod-2",
        "type": "vm_instance",
        "service_id": "compute-engine",
        "project_id": "cc-lab-shop-prod",
        "region": "us-central1",
        "zone": "us-central1-a",
        "status": "RUNNING",
        "machine_type": "e2-standard-2",
        "sku": "E2 instance core hours",
        "base_daily_cost": 0.26,
        "always_on": True,
    },
    {
        "resource_id": "vm-shop-web-prod-1",
        "resource_name": "shop-web-prod-1",
        "type": "vm_instance",
        "service_id": "compute-engine",
        "project_id": "cc-lab-shop-prod",
        "region": "us-central1",
        "zone": "us-central1-b",
        "status": "RUNNING",
        "machine_type": "e2-small",
        "sku": "E2 instance core hours",
        "base_daily_cost": 0.12,
        "always_on": True,
    },
    {
        # Scenario 2: oversized VM (e2-standard-4 at ~11% CPU).
        "resource_id": "vm-etl-staging-1",
        "resource_name": "etl-staging-1",
        "type": "vm_instance",
        "service_id": "compute-engine",
        "project_id": "cc-lab-shop-staging",
        "region": "asia-southeast2",
        "zone": "asia-southeast2-b",
        "status": "RUNNING",
        "machine_type": "e2-standard-4",
        "sku": "E2 instance core hours",
        "base_daily_cost": 0.22,
        "always_on": True,
    },
    {
        "resource_id": "vm-sandbox-dev-1",
        "resource_name": "sandbox-dev-1",
        "type": "vm_instance",
        "service_id": "compute-engine",
        "project_id": "cc-lab-shop-dev",
        "region": "us-central1",
        "zone": "us-central1-c",
        "status": "RUNNING",
        "machine_type": "e2-medium",
        "sku": "E2 instance core hours",
        "base_daily_cost": 0.10,
        "always_on": True,
        "weekday_only": True,
    },
    {
        # Scenario 1: idle VM (~2% CPU, minimal network).
        "resource_id": "vm-report-dev-1",
        "resource_name": "report-dev-1",
        "type": "vm_instance",
        "service_id": "compute-engine",
        "project_id": "cc-lab-shop-dev",
        "region": "us-central1",
        "zone": "us-central1-c",
        "status": "RUNNING",
        "machine_type": "e2-small",
        "sku": "E2 instance core hours",
        "base_daily_cost": 0.07,
        "always_on": True,
        "weekday_only": True,
    },
    {
        # Scenario 8: unallocated cost (resource with no ownership labels).
        "resource_id": "vm-legacy-sandbox-1",
        "resource_name": "legacy-sandbox-1",
        "type": "vm_instance",
        "service_id": "compute-engine",
        "project_id": "cc-lab-legacy-sandbox",
        "region": "us-central1",
        "zone": "us-central1-a",
        "status": "RUNNING",
        "machine_type": "e2-medium",
        "sku": "E2 instance core hours",
        "base_daily_cost": 0.10,
        "always_on": True,
        "weekday_only": True,
    },
    # --- Cloud SQL ---
    {
        "resource_id": "sql-shop-orders-prod",
        "resource_name": "shop-orders-prod",
        "type": "sql_instance",
        "service_id": "cloud-sql",
        "project_id": "cc-lab-shop-prod",
        "region": "us-central1",
        "zone": None,
        "status": "RUNNABLE",
        "machine_type": "db-custom-4-16384",
        "sku": "Cloud SQL for PostgreSQL instance hours",
        "base_daily_cost": 0.55,
        "always_on": True,
    },
    {
        # Scenario 7: underutilized Cloud SQL.
        "resource_id": "sql-shop-orders-staging",
        "resource_name": "shop-orders-staging",
        "type": "sql_instance",
        "service_id": "cloud-sql",
        "project_id": "cc-lab-shop-staging",
        "region": "asia-southeast2",
        "zone": None,
        "status": "RUNNABLE",
        "machine_type": "db-custom-1-3840",
        "sku": "Cloud SQL for PostgreSQL instance hours",
        "base_daily_cost": 0.12,
        "always_on": True,
    },
    # --- Cloud Storage ---
    {
        "resource_id": "gcs-shop-assets-prod",
        "resource_name": "shop-assets-prod",
        "type": "storage_bucket",
        "service_id": "cloud-storage",
        "project_id": "cc-lab-shop-prod",
        "region": "us-central1",
        "zone": None,
        "status": "ACTIVE",
        "machine_type": None,
        "sku": "Cloud Storage standard storage",
        "base_daily_cost": 0.05,
        "always_on": True,
    },
    {
        "resource_id": "gcs-shop-exports-staging",
        "resource_name": "shop-exports-staging",
        "type": "storage_bucket",
        "service_id": "cloud-storage",
        "project_id": "cc-lab-shop-staging",
        "region": "asia-southeast2",
        "zone": None,
        "status": "ACTIVE",
        "machine_type": None,
        "sku": "Cloud Storage standard storage",
        "base_daily_cost": 0.02,
        "always_on": True,
    },
    # --- Artifact Registry ---
    {
        "resource_id": "ar-shop-apps-prod",
        "resource_name": "shop-apps-prod",
        "type": "docker_registry",
        "service_id": "artifact-registry",
        "project_id": "cc-lab-shop-prod",
        "region": "us-central1",
        "zone": None,
        "status": "ACTIVE",
        "machine_type": None,
        "sku": "Artifact Registry storage",
        "base_daily_cost": 0.015,
        "always_on": True,
    },
]

# Utilization profiles: (base, jitter) per metric; None = metric not exposed.
# Scenario hooks: vm-etl-staging-1 is oversized, vm-report-dev-1 is idle.
USAGE_PROFILES: dict[str, dict[str, tuple[float, float] | None]] = {
    "vm-shop-api-prod-1": {
        "cpu": (42, 8),
        "mem": (55, 6),
        "disk": (35, 5),
        "net_in": (2200, 200),
        "net_out": (3100, 300),
    },
    "vm-shop-api-prod-2": {
        "cpu": (38, 8),
        "mem": (52, 6),
        "disk": (32, 5),
        "net_in": (1800, 200),
        "net_out": (2400, 250),
    },
    "vm-shop-web-prod-1": {
        "cpu": (30, 6),
        "mem": (48, 5),
        "disk": (25, 4),
        "net_in": (4200, 400),
        "net_out": (5600, 500),
    },
    "vm-etl-staging-1": {
        "cpu": (11, 3),
        "mem": (30, 4),
        "disk": (28, 3),
        "net_in": (900, 100),
        "net_out": (700, 80),
    },
    "vm-sandbox-dev-1": {
        "cpu": (28, 8),
        "mem": (40, 6),
        "disk": (22, 4),
        "net_in": (300, 40),
        "net_out": (250, 40),
    },
    "vm-report-dev-1": {
        "cpu": (2.4, 1.0),
        "mem": (11, 3),
        "disk": (12, 2),
        "net_in": (12, 3),
        "net_out": (8, 2),
    },
    "vm-legacy-sandbox-1": {
        "cpu": (14, 6),
        "mem": (33, 5),
        "disk": (30, 4),
        "net_in": (150, 30),
        "net_out": (120, 25),
    },
    "sql-shop-orders-prod": {
        "cpu": (32, 6),
        "mem": (62, 5),
        "disk": (45, 3),
        "net_in": (1400, 150),
        "net_out": (1600, 150),
    },
    "sql-shop-orders-staging": {
        "cpu": (12, 4),
        "mem": (38, 4),
        "disk": (30, 3),
        "net_in": (200, 30),
        "net_out": (150, 25),
    },
    "gcs-shop-assets-prod": {
        "cpu": None,
        "mem": None,
        "disk": None,
        "net_in": (60, 10),
        "net_out": (240, 40),
    },
    "gcs-shop-exports-staging": {
        "cpu": None,
        "mem": None,
        "disk": None,
        "net_in": (15, 4),
        "net_out": (45, 10),
    },
    "ar-shop-apps-prod": {
        "cpu": None,
        "mem": None,
        "disk": None,
        "net_in": (5, 2),
        "net_out": (40, 8),
    },
}
REQUEST_COUNT: dict[str, tuple[float, float]] = {
    "gcs-shop-assets-prod": (5200, 800),
    "gcs-shop-exports-staging": (900, 150),
    "ar-shop-apps-prod": (380, 60),
}
# Slow, deterministic storage growth (GB per day from DATE_START).
STORAGE_GROWTH_GB = {
    "gcs-shop-assets-prod": (118.0, 0.04),
    "gcs-shop-exports-staging": (26.0, 0.01),
    "ar-shop-apps-prod": (8.2, 0.01),
}


def daterange(start: date, end: date):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def environment_of(project_id: str) -> str:
    return next(p["environment"] for p in PROJECTS if p["project_id"] == project_id)


def labels_of(project_id: str, resource: dict) -> dict[str, str]:
    merged = dict(next(p["labels"] for p in PROJECTS if p["project_id"] == project_id))
    if resource.get("owner"):
        merged["owner"] = resource["owner"]
    if resource.get("team"):
        merged["team"] = resource["team"]
    if resource.get("application"):
        merged["application"] = resource["application"]
    return merged


def build_projects() -> list[dict]:
    return [dict(p) for p in PROJECTS]


def build_services() -> list[dict]:
    return [{"service_id": sid, **spec} for sid, spec in SERVICES.items()]


def build_resources() -> list[dict]:
    out: list[dict] = []
    for r in RESOURCES:
        owner = "rifky" if r["project_id"] != "cc-lab-legacy-sandbox" else None
        team = "platform" if r["project_id"] != "cc-lab-legacy-sandbox" else None
        app = "shop" if r["project_id"] != "cc-lab-legacy-sandbox" else None
        out.append(
            {
                "resource_id": r["resource_id"],
                "resource_name": r["resource_name"],
                "type": r["type"],
                "service_id": r["service_id"],
                "project_id": r["project_id"],
                "region": r["region"],
                "zone": r["zone"],
                "status": r["status"],
                "environment": environment_of(r["project_id"]),
                "machine_type": r["machine_type"],
                "owner": owner,
                "team": team,
                "application": app,
                "labels": labels_of(
                    r["project_id"], {"owner": owner, "team": team, "application": app}
                ),
                "created_at": "2026-03-02T09:00:00Z",
                "last_seen": END_TS,
                "_base_daily_cost": r["base_daily_cost"],  # stripped before writing
            }
        )
    return out


def build_cost_rows(resources: list[dict]) -> list[dict]:
    rng = random.Random(COST_SEED)
    rows: list[dict] = []
    for res in resources:
        spec = next(r for r in RESOURCES if r["resource_id"] == res["resource_id"])
        base = res.pop("_base_daily_cost")
        for day in daterange(DATE_START, DATE_END):
            multiplier = MONTH_MULTIPLIER[day.month]
            if (
                SPIKE_START <= day <= SPIKE_END
                and spec["service_id"] == "compute-engine"
            ):
                multiplier *= SPIKE_FACTOR
            if day.month == 9 and res["project_id"] in SEPT_DEV_BOOST_PROJECTS:
                multiplier *= SEPT_DEV_BOOST
            if spec.get("weekday_only") and day.weekday() >= 5:
                multiplier *= WEEKEND_FACTOR
            multiplier *= rng.uniform(0.97, 1.03)  # seeded jitter for realistic shape
            cost = round(base * multiplier, 4)
            credits = (
                round(cost * PROD_CREDIT_RATE, 4)
                if res["project_id"] == "cc-lab-shop-prod"
                else 0.0
            )
            if spec["service_id"] in ("cloud-storage", "artifact-registry"):
                size0, growth = STORAGE_GROWTH_GB[res["resource_id"]]
                usage_amount = round(size0 + growth * (day - DATE_START).days, 2)
                usage_unit = "gibibyte month"
            else:
                usage_amount = 24.0
                usage_unit = "hours"
            rows.append(
                {
                    "resource_id": res["resource_id"],
                    "project_id": res["project_id"],
                    "service_id": spec["service_id"],
                    "sku": spec["sku"],
                    "region": res["region"],
                    "usage_date": day.isoformat(),
                    "usage_amount": usage_amount,
                    "usage_unit": usage_unit,
                    "cost": cost,
                    "credits": credits,
                    "net_cost": round(cost - credits, 4),
                    "currency": "USD",
                    "environment": res["environment"],
                    "labels": res["labels"],
                }
            )
    return rows


def build_usage_rows() -> list[dict]:
    rng = random.Random(USAGE_SEED)
    rows: list[dict] = []
    for spec in RESOURCES:
        profile = USAGE_PROFILES[spec["resource_id"]]
        for day in daterange(DATE_START, DATE_END):
            weekend = day.weekday() >= 5 and spec.get("weekday_only", False)
            row: dict = {
                "resource_id": spec["resource_id"],
                "usage_date": day.isoformat(),
            }
            for key, column in (
                ("cpu", "cpu_utilization"),
                ("mem", "memory_utilization"),
                ("disk", "disk_utilization"),
            ):
                metric = profile[key]
                if metric is None:
                    row[column] = None
                    continue
                base, jitter = metric
                value = base * (WEEKEND_FACTOR if weekend else 1.0)
                row[column] = round(max(0.0, value + rng.uniform(-jitter, jitter)), 2)
            for key, column in (
                ("net_in", "network_in_mb"),
                ("net_out", "network_out_mb"),
            ):
                metric = profile[key]
                if metric is None:
                    row[column] = None
                    continue
                base, jitter = metric
                value = base * (WEEKEND_FACTOR if weekend else 1.0)
                row[column] = round(max(0.0, value + rng.uniform(-jitter, jitter)), 1)
            requests = REQUEST_COUNT.get(spec["resource_id"])
            row["request_count"] = (
                round(requests[0] + rng.uniform(-requests[1], requests[1]))
                if requests
                else None
            )
            row["latency_ms"] = (
                None  # VM/bucket level metrics; app-level latency arrives with Phase 3+
            )
            row["error_rate_pct"] = (
                round(rng.uniform(0.0, 0.2), 3) if requests else None
            )
            rows.append(row)
    return rows


def main() -> None:
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    projects = build_projects()
    resources = build_resources()
    cost_rows = build_cost_rows(resources)
    usage_rows = build_usage_rows()

    payloads = {
        "projects.json": projects,
        "services.json": build_services(),
        "resources.json": resources,
        "cost.json": cost_rows,
        "usage.json": usage_rows,
    }
    for name, payload in payloads.items():
        path = MOCK_DIR / name
        path.write_text(
            json.dumps(payload, indent=1, sort_keys=False) + "\n", encoding="utf-8"
        )
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(payload)} rows)")

    monthly: dict[str, float] = {}
    for row in cost_rows:
        month = row["usage_date"][:7]
        monthly[month] = monthly.get(month, 0.0) + row["cost"]
    print("monthly gross cost:", {k: round(v, 2) for k, v in sorted(monthly.items())})
    environments = sorted({r["environment"] for r in resources})
    services = sorted({r["service_id"] for r in resources})
    print("environments covered:", environments)
    print("services covered:", services)


if __name__ == "__main__":
    main()
