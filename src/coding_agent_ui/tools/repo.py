"""Repository inspection tool."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from coding_agent_ui.tools.base import BaseTool


class RepoInspectInput(BaseModel):
    """Input for repository inspection."""

    path: str = Field(default=".")
    max_depth: int = Field(default=3, ge=0)
    max_files: int = Field(default=500, ge=1)


class RepoInspectOutput(BaseModel):
    """Output for repository inspection."""

    root: str
    tree: str
    files: List[str]


class RepoInspectTool(BaseTool[RepoInspectInput, RepoInspectOutput]):
    """Inspect repository structure with a bounded tree view."""

    name = "repo_inspect"
    description = "Inspect repository structure and return a bounded tree."
    input_model = RepoInspectInput
    output_model = RepoInspectOutput

    def run(self, data: RepoInspectInput) -> RepoInspectOutput:
        root = Path(data.path).resolve()
        tree_lines: List[str] = []
        files: List[str] = []

        for dirpath, dirnames, filenames in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            depth = len(rel.parts) if rel.parts else 0
            if depth > data.max_depth:
                dirnames[:] = []
                continue

            indent = "  " * depth
            name = root.name if depth == 0 else Path(dirpath).name
            tree_lines.append(f"{indent}{name}/")

            for filename in sorted(filenames):
                if len(files) >= data.max_files:
                    break
                file_path = Path(dirpath) / filename
                rel_path = str(file_path.relative_to(root))
                files.append(rel_path)
                tree_lines.append(f"{indent}  {filename}")

            if len(files) >= data.max_files:
                tree_lines.append(f"{indent}  ... (truncated)")
                break

        tree = "\n".join(tree_lines)
        return RepoInspectOutput(root=str(root), tree=tree, files=files)
