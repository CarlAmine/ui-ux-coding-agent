"""Accessibility validation tool."""

from __future__ import annotations

from coding_agent_ui.tools.base import BaseTool
from coding_agent_ui.tools.command import CommandInput, CommandOutput, run_command


class AccessibilityTool(BaseTool[CommandInput, CommandOutput]):
    """Run accessibility checks via subprocess."""

    name = "run_accessibility"
    description = "Run accessibility checks and capture output."
    input_model = CommandInput
    output_model = CommandOutput

    def run(self, data: CommandInput) -> CommandOutput:
        return run_command(data)
