"""File system tools."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from coding_agent_ui.tools.base import BaseTool


class ReadFileInput(BaseModel):
    """Input for reading a file."""

    path: str


class ReadFileOutput(BaseModel):
    """Output of a file read."""

    content: str


class WriteFileInput(BaseModel):
    """Input for writing a file."""

    path: str
    content: str
    overwrite: bool = Field(default=True)


class WriteFileOutput(BaseModel):
    """Output of a file write."""

    status: str


def _resolve_path(path: str, root: Optional[str]) -> Path:
    candidate = Path(path)
    if root is None:
        return candidate.resolve()

    root_path = Path(root).resolve()
    resolved = candidate if candidate.is_absolute() else root_path / candidate
    resolved = resolved.resolve()

    if resolved != root_path and root_path not in resolved.parents:
        raise ValueError(f"Path escapes root: {resolved}")
    return resolved


class ReadFileTool(BaseTool[ReadFileInput, ReadFileOutput]):
    """Read a UTF-8 text file from disk."""

    name = "read_file"
    description = "Read a UTF-8 text file from disk."
    input_model = ReadFileInput
    output_model = ReadFileOutput

    def __init__(self, root: Optional[str] = None) -> None:
        self._root = root

    def run(self, data: ReadFileInput) -> ReadFileOutput:
        path = _resolve_path(data.path, self._root)
        content = path.read_text(encoding="utf-8")
        return ReadFileOutput(content=content)


class WriteFileTool(BaseTool[WriteFileInput, WriteFileOutput]):
    """Write a UTF-8 text file to disk."""

    name = "write_file"
    description = "Write a UTF-8 text file to disk."
    input_model = WriteFileInput
    output_model = WriteFileOutput

    def __init__(self, root: Optional[str] = None) -> None:
        self._root = root

    def run(self, data: WriteFileInput) -> WriteFileOutput:
        path = _resolve_path(data.path, self._root)
        if path.exists() and not data.overwrite:
            raise FileExistsError(f"File already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data.content, encoding="utf-8")
        return WriteFileOutput(status="ok")
