"""Resource inventory service.

Provides resource listing, filtering, pagination, and detail views
including cost and utilization data linked to each resource.
"""

from datetime import date, timedelta
from typing import Optional

from app.services.mock_data import (
    BASE_DAILY_COSTS,
    POTENTIAL_SAVINGS,
    RESOURCE_LABELS,
    RESOURCE_UTILIZATION,
    RESOURCES,
    SERVICES,
    generate_cost_records,
    generate_utilization_records,
)


class ResourceService:
    def _get_service_name(self, service_id: str) -> str:
        for s in SERVICES:
            if s["service_id"] == service_id:
                return s["service_name"]
        return service_id

    def _monthly_cost(self, resource_id: str) -> float:
        base_daily = BASE_DAILY_COSTS.get(resource_id, 0.0)
        return round(base_daily * 30, 2)

    def _current_utilization(self, resource_id: str) -> dict:
        util = RESOURCE_UTILIZATION.get(resource_id, {})
        return {
            "cpu": util.get("cpu_avg"),
            "memory": util.get("memory_avg"),
            "disk": util.get("disk_avg"),
        }

    def list_resources(
        self,
        project: Optional[str] = None,
        service: Optional[str] = None,
        region: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        team: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        filtered = list(RESOURCES)

        if project:
            filtered = [r for r in filtered if r["project_id"] == project]
        if service:
            filtered = [r for r in filtered if r["service_id"] == service]
        if region:
            filtered = [r for r in filtered if r["region"] == region]
        if environment:
            filtered = [r for r in filtered if r["environment"] == environment]
        if status:
            filtered = [r for r in filtered if r["status"] == status]
        if owner:
            filtered = [r for r in filtered if r["owner"] == owner]
        if team:
            filtered = [r for r in filtered if r["team"] == team]

        total = len(filtered)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = filtered[start:end]

        data = []
        for r in page_items:
            util = self._current_utilization(r["resource_id"])
            data.append({
                "resource_id": r["resource_id"],
                "name": r["resource_name"],
                "type": r["resource_type"],
                "project": r["project_id"],
                "service": self._get_service_name(r["service_id"]),
                "region": r["region"],
                "zone": r["zone"],
                "environment": r["environment"],
                "status": r["status"],
                "owner": r["owner"],
                "team": r["team"],
                "application": r["application"],
                "monthly_cost": self._monthly_cost(r["resource_id"]),
                "cpu_utilization": util["cpu"],
                "memory_utilization": util["memory"],
                "potential_saving": POTENTIAL_SAVINGS.get(r["resource_id"], 0.0),
            })

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_resource(self, resource_id: str) -> Optional[dict]:
        resource = None
        for r in RESOURCES:
            if r["resource_id"] == resource_id:
                resource = r
                break

        if resource is None:
            return None

        end_date = date(2026, 8, 26)
        start_date = end_date.replace(day=1)

        cost_records = generate_cost_records(start_date=start_date, end_date=end_date)
        resource_costs = [
            c for c in cost_records if c["resource_id"] == resource_id
        ]
        monthly_cost = sum(c["net_cost"] for c in resource_costs)

        cost_history = []
        for c in resource_costs:
            cost_history.append({
                "date": c["usage_date"].isoformat(),
                "cost": round(c["net_cost"], 4),
            })

        utilization = generate_utilization_records(resource_id)
        util_summary = RESOURCE_UTILIZATION.get(resource_id, {})
        labels = RESOURCE_LABELS.get(resource_id, {})

        created_at = (end_date - timedelta(days=120)).isoformat()
        last_seen = end_date.isoformat()

        return {
            "resource_id": resource["resource_id"],
            "name": resource["resource_name"],
            "type": resource["resource_type"],
            "project": resource["project_id"],
            "service": self._get_service_name(resource["service_id"]),
            "service_id": resource["service_id"],
            "region": resource["region"],
            "zone": resource["zone"],
            "environment": resource["environment"],
            "status": resource["status"],
            "owner": resource["owner"],
            "team": resource["team"],
            "application": resource["application"],
            "labels": labels,
            "created_at": created_at,
            "last_seen": last_seen,
            "monthly_cost": round(monthly_cost, 2),
            "potential_saving": POTENTIAL_SAVINGS.get(resource_id, 0.0),
            "utilization": {
                "cpu_avg": util_summary.get("cpu_avg"),
                "memory_avg": util_summary.get("memory_avg"),
                "disk_avg": util_summary.get("disk_avg"),
            },
            "utilization_history": utilization,
            "cost_history": cost_history,
        }


resource_service = ResourceService()
