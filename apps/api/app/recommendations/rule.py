"""Base interface for recommendation rules."""

from abc import ABC, abstractmethod


class RecommendationRule(ABC):
    """Base class for all recommendation rules.

    Each rule must implement these methods to generate evidence-based
    recommendations without making automatic infrastructure changes.
    """

    @abstractmethod
    def evaluate(self, resource: dict, metrics: dict) -> bool:
        """Evaluate if this rule applies to the given resource.

        Args:
            resource: Resource metadata (id, name, type, service, cost, etc.)
            metrics: Resource metrics (cpu, memory, disk utilization, etc.)

        Returns:
            True if recommendation applies, False otherwise
        """
        pass

    @abstractmethod
    def explain(self, resource: dict, metrics: dict) -> dict:
        """Generate detailed explanation with evidence.

        Returns:
            dict with:
                - title: brief recommendation title
                - problem: what's wrong
                - evidence: observed data supporting the recommendation
                - recommendation: what action to take
        """
        pass

    @abstractmethod
    def calculate_saving(self, resource: dict, metrics: dict) -> float:
        """Calculate potential monthly savings in USD.

        Must be evidence-based, not guessed.

        Returns:
            Estimated monthly savings (USD)
        """
        pass

    @abstractmethod
    def calculate_risk(self, resource: dict, metrics: dict) -> str:
        """Assess risk level of implementing this recommendation.

        Returns:
            "LOW", "MEDIUM", or "HIGH"
        """
        pass

    @abstractmethod
    def confidence(self, resource: dict, metrics: dict) -> str:
        """Express confidence in the recommendation.

        Returns:
            "HIGH", "MEDIUM", or "LOW"
        """
        pass

    def effort(self, resource: dict, metrics: dict) -> str:
        """Estimate implementation effort.

        Default: "LOW" (can be overridden).

        Returns:
            "LOW", "MEDIUM", or "HIGH"
        """
        return "LOW"

    def priority_score(self, resource: dict, metrics: dict) -> int:
        """Calculate priority score based on savings, risk, and confidence.

        Higher score = higher priority.
        Default implementation balances savings against risk.

        Returns:
            Priority score (0-100)
        """
        saving = self.calculate_saving(resource, metrics)
        risk = self.calculate_risk(resource, metrics)
        conf = self.confidence(resource, metrics)

        risk_penalty = {"LOW": 0, "MEDIUM": 20, "HIGH": 40}
        conf_bonus = {"HIGH": 30, "MEDIUM": 15, "LOW": 0}

        score = min(saving * 2, 50) + conf_bonus[conf] - risk_penalty[risk]
        return max(0, min(100, int(score)))
