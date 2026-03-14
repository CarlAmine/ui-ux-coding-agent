"""Frontend agent policy rules."""

from __future__ import annotations

from typing import List

from coding_agent_ui.agent_core.policy import BasePolicy


class FrontendPolicy(BasePolicy):
    """Policy rules for UI/UX-oriented behavior."""

    def rules(self) -> List[str]:
        return [
            "Prefer existing design-system tokens and components",
            "Improve visual hierarchy and information structure",
            "Normalize spacing and alignment for consistent layout",
            "Increase readability (typography, line length, contrast)",
            "Preserve and improve responsive behavior across breakpoints",
            "Treat accessibility as a default requirement (labels, focus, contrast, semantics)",
            "Include loading, empty, error, and validation states when relevant",
            "Ensure validation plan covers accessibility and responsive checks when configured",
            "Avoid broad refactors unless explicitly required",
        ]
