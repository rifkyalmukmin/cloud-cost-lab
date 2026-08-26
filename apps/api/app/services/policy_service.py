"""Policy evaluation service.

Evaluates resources against governance policies and generates
warnings/recommendations. No automatic destructive actions.
"""

from app.governance.policies import ALL_POLICIES
from app.services.mock_data import RESOURCES, SERVICES


class PolicyService:
    def _get_service_name(self, service_id: str) -> str:
        for s in SERVICES:
            if s["service_id"] == service_id:
                return s["service_name"]
        return service_id

    def evaluate_policies(self) -> dict:
        """Evaluate all policies against all resources."""
        results = []

        for resource in RESOURCES:
            resource_data = {
                "resource_id": resource["resource_id"],
                "name": resource["resource_name"],
                "service": self._get_service_name(resource["service_id"]),
                "environment": resource["environment"],
                "owner": resource["owner"],
                "team": resource["team"],
                "monthly_cost": 0.0,
                "public_access": False,
                "scheduled": False,
            }

            from app.services.mock_data import BASE_DAILY_COSTS
            resource_data["monthly_cost"] = round(BASE_DAILY_COSTS.get(resource["resource_id"], 0.0) * 30, 2)

            policy_results = []
            for policy in ALL_POLICIES:
                result = policy.evaluate(resource_data)
                policy_results.append({
                    "policy": policy.name(),
                    "status": result["status"],
                    "message": result["message"],
                    "recommendation": result.get("recommendation"),
                })

            results.append({
                "resource_id": resource_data["resource_id"],
                "resource_name": resource_data["name"],
                "service": resource_data["service"],
                "environment": resource_data["environment"],
                "policy_results": policy_results,
            })

        violation_count = sum(
            1 for r in results
            for p in r["policy_results"]
            if p["status"] == "VIOLATION"
        )
        warning_count = sum(
            1 for r in results
            for p in r["policy_results"]
            if p["status"] == "WARNING"
        )
        pass_count = sum(
            1 for r in results
            for p in r["policy_results"]
            if p["status"] == "PASS"
        )

        policy_summary = []
        for policy in ALL_POLICIES:
            policy_summary.append({
                "name": policy.name(),
                "description": policy.description(),
            })

        return {
            "summary": {
                "total_resources": len(RESOURCES),
                "total_policies": len(ALL_POLICIES),
                "violations": violation_count,
                "warnings": warning_count,
                "passed": pass_count,
            },
            "policies": policy_summary,
            "results": results,
        }


policy_service = PolicyService()
