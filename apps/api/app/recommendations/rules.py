"""Concrete recommendation rules."""

from app.recommendations.rule import RecommendationRule


class IdleComputeRule(RecommendationRule):
    """Detects compute resources with consistently low utilization."""

    def evaluate(self, resource: dict, metrics: dict) -> bool:
        if "compute" not in resource.get("service", "").lower():
            return False
        cpu_avg = metrics.get("cpu_avg")
        if cpu_avg is None:
            return False
        return cpu_avg < 5.0

    def explain(self, resource: dict, metrics: dict) -> dict:
        cpu_avg = metrics.get("cpu_avg", 0)
        return {
            "title": "Idle compute resource detected",
            "problem": f"Resource is running but barely utilized (CPU avg: {cpu_avg:.1f}%)",
            "evidence": f"Observed CPU utilization averaged {cpu_avg:.1f}% over 30 days, indicating the resource is idle or rarely used",
            "recommendation": "Consider scheduling this resource (start/stop on demand) or decommissioning if no longer needed",
        }

    def calculate_saving(self, resource: dict, metrics: dict) -> float:
        monthly_cost = resource.get("monthly_cost", 0.0)
        return round(monthly_cost * 0.90, 2)

    def calculate_risk(self, resource: dict, metrics: dict) -> str:
        if resource.get("environment") == "production":
            return "MEDIUM"
        return "LOW"

    def confidence(self, resource: dict, metrics: dict) -> str:
        cpu_avg = metrics.get("cpu_avg", 0)
        if cpu_avg < 2.0:
            return "HIGH"
        elif cpu_avg < 5.0:
            return "MEDIUM"
        return "LOW"


class OversizedComputeRule(RecommendationRule):
    """Detects compute resources that are larger than needed."""

    def evaluate(self, resource: dict, metrics: dict) -> bool:
        if "compute" not in resource.get("service", "").lower():
            return False
        cpu_avg = metrics.get("cpu_avg")
        mem_avg = metrics.get("memory_avg")
        if cpu_avg is None or mem_avg is None:
            return False
        return cpu_avg < 20.0 and mem_avg < 40.0

    def explain(self, resource: dict, metrics: dict) -> dict:
        cpu_avg = metrics.get("cpu_avg", 0)
        mem_avg = metrics.get("memory_avg", 0)
        return {
            "title": "Resource is oversized for current workload",
            "problem": f"Low resource utilization (CPU: {cpu_avg:.1f}%, Memory: {mem_avg:.1f}%)",
            "evidence": f"CPU averaged {cpu_avg:.1f}% and memory averaged {mem_avg:.1f}% over 30 days, indicating the instance is larger than needed",
            "recommendation": "Consider downsizing to a smaller instance type (e.g., reduce from e2-standard-4 to e2-standard-2)",
        }

    def calculate_saving(self, resource: dict, metrics: dict) -> float:
        monthly_cost = resource.get("monthly_cost", 0.0)
        return round(monthly_cost * 0.40, 2)

    def calculate_risk(self, resource: dict, metrics: dict) -> str:
        cpu_avg = metrics.get("cpu_avg", 0)
        if cpu_avg < 10.0:
            return "LOW"
        elif cpu_avg < 20.0:
            return "MEDIUM"
        return "HIGH"

    def confidence(self, resource: dict, metrics: dict) -> str:
        cpu_avg = metrics.get("cpu_avg", 0)
        mem_avg = metrics.get("memory_avg", 0)
        if cpu_avg < 15.0 and mem_avg < 30.0:
            return "HIGH"
        elif cpu_avg < 20.0 and mem_avg < 40.0:
            return "MEDIUM"
        return "LOW"

    def effort(self, resource: dict, metrics: dict) -> str:
        return "MEDIUM"


class UnusedDiskRule(RecommendationRule):
    """Detects unattached or unused disks."""

    def evaluate(self, resource: dict, metrics: dict) -> bool:
        if resource.get("status") == "unattached":
            return True
        disk_util = metrics.get("disk_avg")
        if disk_util is not None and disk_util < 10.0:
            return True
        return False

    def explain(self, resource: dict, metrics: dict) -> dict:
        status = resource.get("status")
        disk_util = metrics.get("disk_avg")
        if status == "unattached":
            return {
                "title": "Unattached disk detected",
                "problem": "Disk is not attached to any instance but still incurring costs",
                "evidence": "Disk status is 'unattached' — no VM is using this disk",
                "recommendation": "Review if disk data is still needed. If not, delete the disk. If needed, create a snapshot first.",
            }
        else:
            return {
                "title": "Disk is barely used",
                "problem": f"Disk utilization is very low ({disk_util:.1f}%)",
                "evidence": f"Disk utilization averaged {disk_util:.1f}% over 30 days",
                "recommendation": "Consider consolidating with other disks or using a smaller disk size",
            }

    def calculate_saving(self, resource: dict, metrics: dict) -> float:
        monthly_cost = resource.get("monthly_cost", 0.0)
        if resource.get("status") == "unattached":
            return round(monthly_cost, 2)
        return round(monthly_cost * 0.50, 2)

    def calculate_risk(self, resource: dict, metrics: dict) -> str:
        if resource.get("status") == "unattached":
            return "LOW"
        return "MEDIUM"

    def confidence(self, resource: dict, metrics: dict) -> str:
        if resource.get("status") == "unattached":
            return "HIGH"
        return "MEDIUM"


class StorageRetentionRule(RecommendationRule):
    """Detects opportunities to optimize storage retention."""

    def evaluate(self, resource: dict, metrics: dict) -> bool:
        service = resource.get("service", "").lower()
        if "storage" not in service and "artifact" not in service:
            return False
        monthly_cost = resource.get("monthly_cost", 0.0)
        return monthly_cost > 1.0

    def explain(self, resource: dict, metrics: dict) -> dict:
        return {
            "title": "Review storage retention policy",
            "problem": "Storage costs are accumulating without a defined retention policy",
            "evidence": "Storage is growing without automatic cleanup or lifecycle policies",
            "recommendation": "Implement lifecycle policies: move old data to cold storage, delete stale artifacts, set retention limits",
        }

    def calculate_saving(self, resource: dict, metrics: dict) -> float:
        monthly_cost = resource.get("monthly_cost", 0.0)
        return round(monthly_cost * 0.30, 2)

    def calculate_risk(self, resource: dict, metrics: dict) -> str:
        return "LOW"

    def confidence(self, resource: dict, metrics: dict) -> str:
        return "MEDIUM"

    def effort(self, resource: dict, metrics: dict) -> str:
        return "MEDIUM"


class CostAnomalyRule(RecommendationRule):
    """Detects resources with unexpected cost increases."""

    def evaluate(self, resource: dict, metrics: dict) -> bool:
        cost_change = metrics.get("cost_change_pct", 0.0)
        return cost_change > 50.0

    def explain(self, resource: dict, metrics: dict) -> dict:
        cost_change = metrics.get("cost_change_pct", 0)
        return {
            "title": "Unexpected cost increase detected",
            "problem": f"Resource cost increased by {cost_change:.0f}% compared to previous period",
            "evidence": f"Cost rose {cost_change:.0f}% — investigate workload changes, traffic spikes, or misconfigurations",
            "recommendation": "Review recent changes to this resource. Check for workload increases, configuration drift, or billing errors.",
        }

    def calculate_saving(self, resource: dict, metrics: dict) -> float:
        return 0.0

    def calculate_risk(self, resource: dict, metrics: dict) -> str:
        return "LOW"

    def confidence(self, resource: dict, metrics: dict) -> str:
        return "HIGH"


ALL_RULES = [
    IdleComputeRule(),
    OversizedComputeRule(),
    UnusedDiskRule(),
    StorageRetentionRule(),
    CostAnomalyRule(),
]
