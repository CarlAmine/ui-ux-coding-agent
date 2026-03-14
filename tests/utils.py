"""Test utilities for the coding agent."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List

from pydantic import BaseModel

from coding_agent_ui.config.settings import Settings


class FakeResponse:
    """Minimal response object with a content attribute."""

    def __init__(self, content: Any) -> None:
        self.content = content


class QueueLLM:
    """LLM stub that returns pre-seeded responses in order."""

    def __init__(self, responses: Iterable[str]) -> None:
        self._responses = list(responses)

    def invoke(self, messages: List[Any]) -> FakeResponse:  # noqa: ARG002
        if not self._responses:
            raise AssertionError("QueueLLM has no more responses queued.")
        return FakeResponse(self._responses.pop(0))


class StubTool:
    """Simple tool stub that returns a computed response."""

    def __init__(self, name: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self.name = name
        self._handler = handler

    def invoke(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        return self._handler(raw_input)


def dumps(model: BaseModel) -> str:
    """Serialize a pydantic model to JSON string."""
    return json.dumps(model.model_dump())


def make_settings(**overrides: Any) -> Settings:
    """Create a Settings instance with defaults suitable for tests."""
    base = dict(
        env="test",
        log_level="INFO",
        llm_provider="stub",
        model_name="",
        temperature=0.0,
        max_tokens=None,
        openai_api_key=None,
        openai_base_url=None,
        openai_organization=None,
        openai_project=None,
        lint_cmd=None,
        test_cmd=None,
        accessibility_cmd=None,
        preview_cmd=None,
        preview_mode="command",
        repo_max_depth=3,
        repo_max_files=200,
        search_max_results=10,
        max_iterations=1,
        edit_max_files=10,
        max_diff_chars=4000,
        max_file_context_chars_per_file=2000,
        max_total_file_context_chars=8000,
        max_repo_tree_chars=2000,
        max_search_result_chars=2000,
    )
    base.update(overrides)
    return Settings(**base)
