"""Code search tool."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from coding_agent_ui.tools.base import BaseTool


class CodeSearchInput(BaseModel):
    """Input for code search."""

    query: str
    path: str = Field(default=".")
    max_results: int = Field(default=50, ge=1)
    case_sensitive: bool = Field(default=False)


class CodeSearchMatch(BaseModel):
    """Single search match."""

    path: str
    line: int
    text: str


class CodeSearchOutput(BaseModel):
    """Search results."""

    matches: List[CodeSearchMatch]


class CodeSearchTool(BaseTool[CodeSearchInput, CodeSearchOutput]):
    """Simple regex search across text files."""

    name = "code_search"
    description = "Search for a query across text files in a path."
    input_model = CodeSearchInput
    output_model = CodeSearchOutput

    def run(self, data: CodeSearchInput) -> CodeSearchOutput:
        flags = 0 if data.case_sensitive else re.IGNORECASE
        pattern = re.compile(data.query, flags=flags)
        root = Path(data.path).resolve()
        matches: List[CodeSearchMatch] = []

        for file_path in root.rglob("*"):
            if file_path.is_dir():
                continue
            if file_path.stat().st_size > 1_000_000:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            for index, line in enumerate(content.splitlines(), start=1):
                if pattern.search(line):
                    matches.append(
                        CodeSearchMatch(
                            path=str(file_path.relative_to(root)),
                            line=index,
                            text=line.strip(),
                        )
                    )
                    if len(matches) >= data.max_results:
                        return CodeSearchOutput(matches=matches)

        return CodeSearchOutput(matches=matches)
