"""Tests for frontend validation hooks."""

from __future__ import annotations

from pathlib import Path

from coding_agent_ui.agent_core.agent import Agent
from coding_agent_ui.agent_core.loop import AgentLoop
from coding_agent_ui.agents.frontend.policy import FrontendPolicy
from coding_agent_ui.tools.fs import ReadFileTool, WriteFileTool
from coding_agent_ui.tools.registry import InMemoryToolRegistry
from tests.utils import StubTool, make_settings


class DummyLLM:
    def invoke(self, messages):  # noqa: ANN001
        raise AssertionError("LLM should not be invoked in validation tests")


def _build_loop(tmp_path: Path, settings_overrides: dict, preview_response: dict) -> AgentLoop:
    tools = InMemoryToolRegistry()
    tools.register(StubTool("repo_inspect", lambda _: {"root": str(tmp_path), "tree": "repo/", "files": []}))
    tools.register(StubTool("code_search", lambda _: {"matches": []}))
    tools.register(ReadFileTool(root=str(tmp_path)))
    tools.register(WriteFileTool(root=str(tmp_path)))
    tools.register(StubTool("run_lint", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))
    tools.register(StubTool("run_tests", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))
    tools.register(StubTool("run_accessibility", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))
    tools.register(StubTool("run_preview", lambda _: preview_response))

    agent = Agent(llm=DummyLLM(), policy=FrontendPolicy(), tools=tools)
    settings = make_settings(**settings_overrides)
    return AgentLoop(agent, settings=settings, repo_root=str(tmp_path), dry_run=False)


def test_validation_includes_accessibility_and_preview(tmp_path: Path) -> None:
    loop = _build_loop(
        tmp_path,
        {
            "accessibility_cmd": "a11y",
            "preview_cmd": "preview",
            "preview_mode": "command",
        },
        {
            "status": "ok",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "artifacts": [],
            "note": None,
        },
    )

    validation = loop._run_validation([])
    run_names = [run.name for run in validation.runs]

    assert "accessibility" in run_names
    assert "preview" in run_names
    assert validation.failures == []


def test_preview_unsupported_skipped(tmp_path: Path) -> None:
    unresolved: list[str] = []
    loop = _build_loop(
        tmp_path,
        {
            "preview_cmd": "preview",
            "preview_mode": "screenshot",
        },
        {
            "status": "unsupported",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "artifacts": [],
            "note": "Screenshot capture is not implemented yet.",
        },
    )

    validation = loop._run_validation(unresolved)

    assert "preview" in validation.skipped
    assert validation.failures == []
    assert any("Screenshot" in note for note in unresolved)
