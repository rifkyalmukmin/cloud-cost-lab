"""Base policy interface."""

from abc import ABC, abstractmethod


class Policy(ABC):
    """Base class for governance policies.

    Policies generate warnings and recommendations, but never take
    automatic destructive actions.
    """

    @abstractmethod
    def name(self) -> str:
        """Policy name."""
        pass

    @abstractmethod
    def description(self) -> str:
        """What this policy enforces."""
        pass

    @abstractmethod
    def evaluate(self, resource: dict) -> dict:
        """Evaluate policy against a resource.

        Returns:
            dict with:
                - status: "PASS" | "WARNING" | "VIOLATION"
                - message: explanation
                - recommendation: what action to take (if not PASS)
        """
        pass
