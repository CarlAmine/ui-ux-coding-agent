"""Registry for available tools."""

from __future__ import annotations

from typing import Dict, List, Protocol

from coding_agent_ui.tools.base import BaseTool


class ToolRegistry(Protocol):
    """Tool registry contract."""

    def list(self) -> List[str]:
        """Return registered tool names."""
        ...

    def get(self, name: str) -> BaseTool:
        """Return a tool by name."""
        ...


class InMemoryToolRegistry:
    """Simple in-memory tool registry."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list(self) -> List[str]:
        """Return registered tool names."""
        return sorted(self._tools.keys())

    def get(self, name: str) -> BaseTool:
        """Return a tool by name."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc
