"""Agent policy interfaces and defaults."""

from __future__ import annotations

from typing import Protocol, List


class AgentPolicy(Protocol):
    """Policy contract for agent behavior."""

    def rules(self) -> List[str]:
        """Return a list of policy rules to inject into prompts."""
        ...


class BasePolicy:
    """Default policy with no additional rules."""

    def rules(self) -> List[str]:
        return []
