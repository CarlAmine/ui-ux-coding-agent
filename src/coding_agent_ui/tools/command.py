"""Shared command execution helpers."""

from __future__ import annotations

import os
import shlex
import subprocess
from typing import List, Optional

from pydantic import BaseModel, Field


class CommandInput(BaseModel):
    """Command execution request."""

    cmd: List[str] = Field(..., description="Command and arguments")
    cwd: Optional[str] = Field(default=None, description="Working directory")
    timeout_seconds: Optional[int] = Field(default=600, description="Timeout in seconds")


class CommandOutput(BaseModel):
    """Command execution result."""

    exit_code: int
    stdout: str
    stderr: str


def parse_command(command: str) -> List[str]:
    """Parse a shell-like command string into args.

    Uses platform-appropriate splitting for Windows vs POSIX.
    """
    if os.name == "nt":
        return shlex.split(command, posix=False)
    return shlex.split(command, posix=True)


def run_command(data: CommandInput) -> CommandOutput:
    """Run a command and capture output."""
    completed = subprocess.run(
        data.cmd,
        cwd=data.cwd,
        capture_output=True,
        text=True,
        timeout=data.timeout_seconds,
        check=False,
    )
    return CommandOutput(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
