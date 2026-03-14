"""Routing utilities for selecting an agent specialization."""

from __future__ import annotations

from typing import Any, Dict


class AgentRouter:
    """Select an agent specialization based on task and context.

    This is a stub. Replace with real routing logic (rules, classifiers, or LLM-based routers)
    once multiple specializations exist.
    """

    def route(self, task: str, context: Dict[str, Any]) -> str:
        """Return the specialization key for the given task."""
        _ = (task, context)
        return "frontend"
