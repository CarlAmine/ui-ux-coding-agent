"""Lint execution tool."""

from __future__ import annotations

from coding_agent_ui.tools.base import BaseTool
from coding_agent_ui.tools.command import CommandInput, CommandOutput, run_command


class LintTool(BaseTool[CommandInput, CommandOutput]):
    """Run lint commands via subprocess."""

    name = "run_lint"
    description = "Run a lint command and capture output."
    input_model = CommandInput
    output_model = CommandOutput

    def run(self, data: CommandInput) -> CommandOutput:
        return run_command(data)
