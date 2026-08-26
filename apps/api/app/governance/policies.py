"""Concrete governance policies."""

from app.governance.policy import Policy


class RequireOwnerLabelPolicy(Policy):
    """Enforces that all resources have an owner label."""

    def name(self) -> str:
        return "REQUIRE_OWNER_LABEL"

    def description(self) -> str:
        return "All resources must have a clearly defined owner"

    def evaluate(self, resource: dict) -> dict:
        owner = resource.get("owner")
        if not owner or owner == "UNALLOCATED":
            return {
                "status": "VIOLATION",
                "message": f"Resource '{resource.get('name')}' has no owner assigned",
                "recommendation": "Assign an owner to enable accountability and cost allocation",
            }
        return {
            "status": "PASS",
            "message": f"Resource owner: {owner}",
            "recommendation": None,
        }


class RequireEnvironmentLabelPolicy(Policy):
    """Enforces that all resources have an environment label."""

    def name(self) -> str:
        return "REQUIRE_ENVIRONMENT_LABEL"

    def description(self) -> str:
        return "All resources must be tagged with an environment (production, staging, development)"

    def evaluate(self, resource: dict) -> dict:
        env = resource.get("environment")
        if not env or env not in ["production", "staging", "development"]:
            return {
                "status": "VIOLATION",
                "message": f"Resource '{resource.get('name')}' has invalid or missing environment label",
                "recommendation": "Tag resource with environment: production, staging, or development",
            }
        return {
            "status": "PASS",
            "message": f"Environment: {env}",
            "recommendation": None,
        }


class MaxMonthlyCostPolicy(Policy):
    """Enforces maximum monthly cost limits for non-production environments."""

    def name(self) -> str:
        return "MAX_MONTHLY_COST"

    def description(self) -> str:
        return "Development resources must not exceed $100/month per resource"

    def evaluate(self, resource: dict) -> dict:
        env = resource.get("environment")
        cost = resource.get("monthly_cost", 0.0)

        if env == "development" and cost > 100.0:
            return {
                "status": "VIOLATION",
                "message": f"Development resource cost ${cost:.2f}/month exceeds limit ($100)",
                "recommendation": "Downsize resource or review if it should be in development environment",
            }
        elif env == "staging" and cost > 200.0:
            return {
                "status": "WARNING",
                "message": f"Staging resource cost ${cost:.2f}/month is unusually high (threshold: $200)",
                "recommendation": "Review if resource sizing is appropriate for staging workload",
            }
        return {
            "status": "PASS",
            "message": f"Cost ${cost:.2f}/month within acceptable range",
            "recommendation": None,
        }


class NoPublicDatabasePolicy(Policy):
    """Warns about databases that might be publicly accessible."""

    def name(self) -> str:
        return "NO_PUBLIC_DATABASE"

    def description(self) -> str:
        return "Databases should not be publicly accessible"

    def evaluate(self, resource: dict) -> dict:
        service = resource.get("service", "").lower()
        is_db = "sql" in service or "database" in service
        public = resource.get("public_access", False)

        if is_db and public:
            return {
                "status": "VIOLATION",
                "message": f"Database '{resource.get('name')}' is publicly accessible",
                "recommendation": "Restrict database access to private network only",
            }
        return {
            "status": "PASS",
            "message": "Resource access configuration OK",
            "recommendation": None,
        }


class DevResourceSchedulePolicy(Policy):
    """Recommends scheduling for development resources."""

    def name(self) -> str:
        return "DEV_RESOURCE_SCHEDULE"

    def description(self) -> str:
        return "Development compute resources should use scheduling to reduce costs"

    def evaluate(self, resource: dict) -> dict:
        env = resource.get("environment")
        service = resource.get("service", "").lower()
        is_compute = "compute" in service
        scheduled = resource.get("scheduled", False)

        if env == "development" and is_compute and not scheduled:
            return {
                "status": "WARNING",
                "message": f"Development VM '{resource.get('name')}' runs 24/7 without scheduling",
                "recommendation": "Implement start/stop schedule (e.g., business hours only) to save ~60% on compute costs",
            }
        return {
            "status": "PASS",
            "message": "Resource scheduling OK",
            "recommendation": None,
        }


ALL_POLICIES = [
    RequireOwnerLabelPolicy(),
    RequireEnvironmentLabelPolicy(),
    MaxMonthlyCostPolicy(),
    NoPublicDatabasePolicy(),
    DevResourceSchedulePolicy(),
]
