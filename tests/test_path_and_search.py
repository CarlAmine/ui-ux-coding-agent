"""Path normalization and search deduplication tests."""

from __future__ import annotations

from pathlib import Path

from coding_agent_ui.agent_core.agent import Agent
from coding_agent_ui.agent_core.loop import AgentLoop
from coding_agent_ui.agents.base.schemas import AnalysisResult, TaskAnalysis
from coding_agent_ui.agents.frontend.policy import FrontendPolicy
from coding_agent_ui.tools.fs import ReadFileTool, WriteFileTool
from coding_agent_ui.tools.registry import InMemoryToolRegistry
from tests.utils import QueueLLM, StubTool, make_settings


def _build_loop(tmp_path: Path) -> AgentLoop:
    tools = InMemoryToolRegistry()
    tools.register(StubTool("repo_inspect", lambda _: {"root": str(tmp_path), "tree": "repo/", "files": []}))
    tools.register(StubTool("code_search", lambda _: {"matches": []}))
    tools.register(ReadFileTool(root=str(tmp_path)))
    tools.register(WriteFileTool(root=str(tmp_path)))
    tools.register(StubTool("run_lint", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))
    tools.register(StubTool("run_tests", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))

    llm = QueueLLM(["{}"])  # not used in these tests
    agent = Agent(llm=llm, policy=FrontendPolicy(), tools=tools)
    settings = make_settings()
    return AgentLoop(agent, settings=settings, repo_root=str(tmp_path))


def test_path_normalization(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "app.js"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("const a = 1;\n", encoding="utf-8")

    loop = _build_loop(tmp_path)
    rel = loop._normalize_path("src/app.js")
    abs_path = loop._normalize_path(str(file_path))

    assert rel == abs_path
    assert rel == "src/app.js"

    outside = loop._normalize_path(str(tmp_path.parent / "outside.js"))
    assert outside is None


def test_search_deduplication(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "app.js"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("const a = 1;\n", encoding="utf-8")

    abs_path = str(file_path)

    def search_handler(_: dict) -> dict:
        return {
            "matches": [
                {"path": abs_path, "line": 1, "text": "const a = 1;"},
                {"path": "src/app.js", "line": 1, "text": "const a = 1;"},
                {"path": "src/app.js", "line": 2, "text": "const b = 2;"},
                {"path": "src/app.js", "line": 2, "text": "const b = 2;"},
            ]
        }

    loop = _build_loop(tmp_path)
    loop._agent.tools.get("code_search").invoke = search_handler

    analysis = AnalysisResult(
        task_analysis=TaskAnalysis(intent="Search"),
        search_queries=["const"],
        focus_files=[],
    )

    results = loop._search_repo("Search", analysis)

    assert len(results.matches) == 2
    assert all(match.path == "src/app.js" for match in results.matches)
