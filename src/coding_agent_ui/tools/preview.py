"""UI preview and inspection tool."""

from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field

from coding_agent_ui.tools.base import BaseTool
from coding_agent_ui.tools.command import CommandInput, run_command


class PreviewInput(BaseModel):
    """Input for UI preview execution or inspection."""

    cmd: List[str] = Field(..., description="Command to launch or validate preview")
    cwd: Optional[str] = Field(default=None)
    mode: Literal["command", "screenshot"] = Field(
        default="command",
        description="Preview mode: run a command or request screenshots",
    )
    timeout_seconds: Optional[int] = Field(default=600)
    output_dir: Optional[str] = Field(default=None)
    snapshot: bool = Field(default=False)


class PreviewOutput(BaseModel):
    """Output of UI preview execution."""

    status: Literal["ok", "failed", "unsupported"]
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    artifacts: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class PreviewTool(BaseTool[PreviewInput, PreviewOutput]):
    """Run a preview command or return a placeholder for screenshots."""

    name = "run_preview"
    description = "Launch a UI preview or collect inspection artifacts."
    input_model = PreviewInput
    output_model = PreviewOutput

    def run(self, data: PreviewInput) -> PreviewOutput:
        if data.mode == "screenshot":
            return PreviewOutput(
                status="unsupported",
                note=(
                    "Screenshot capture is not implemented yet. "
                    "Provide a command-based preview instead."
                ),
            )

        output = run_command(
            CommandInput(cmd=data.cmd, cwd=data.cwd, timeout_seconds=data.timeout_seconds)
        )
        status = "ok" if output.exit_code == 0 else "failed"
        return PreviewOutput(
            status=status,
            exit_code=output.exit_code,
            stdout=output.stdout,
            stderr=output.stderr,
        )
