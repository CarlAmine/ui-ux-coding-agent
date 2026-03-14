"""Test execution tool."""

from __future__ import annotations

from coding_agent_ui.tools.base import BaseTool
from coding_agent_ui.tools.command import CommandInput, CommandOutput, run_command


class TestTool(BaseTool[CommandInput, CommandOutput]):
    """Run test commands via subprocess."""

    name = "run_tests"
    description = "Run a test command and capture output."
    input_model = CommandInput
    output_model = CommandOutput

    def run(self, data: CommandInput) -> CommandOutput:
        return run_command(data)
