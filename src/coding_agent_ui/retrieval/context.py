"""Context builder interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Protocol


class ContextBuilder(Protocol):
    """Build context for an agent run."""

    def build(self, task: str) -> Dict[str, Any]:
        """Return context for the given task."""
        ...


class DesignGuidanceContextBuilder:
    """Load optional design guidance files from the repo root."""

    def __init__(
        self,
        repo_root: str,
        guidance_files: Iterable[str] | None = None,
        max_chars: int = 20000,
    ) -> None:
        self._root = Path(repo_root).resolve()
        self._guidance_files = list(
            guidance_files
            if guidance_files is not None
            else [
                "design_principles.md",
                "ux_checklist.md",
                "component_guidelines.md",
            ]
        )
        self._max_chars = max_chars

    def build(self, task: str) -> Dict[str, Any]:
        _ = task
        guidance: Dict[str, str] = {}

        for filename in self._guidance_files:
            path = self._root / filename
            if not path.exists() or not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            guidance[filename] = content[: self._max_chars]

        if not guidance:
            return {}

        return {"design_guidance": guidance}


class EmptyContextBuilder:
    """Return an empty context.

    This is a safe default for early iterations.
    """

    def build(self, task: str) -> Dict[str, Any]:
        _ = task
        return {}
