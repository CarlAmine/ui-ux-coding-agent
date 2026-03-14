"""State models for agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from coding_agent_ui.agents.base.schemas import AgentReport


@dataclass(frozen=True)
class AgentRequest:
    """Input payload for an agent run."""

    task: str
    context: Dict[str, Any]


@dataclass(frozen=True)
class AgentResponse:
    """Output payload for an agent run."""

    report: AgentReport
