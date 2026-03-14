"""Partial rollback failure tests."""

from __future__ import annotations

from pathlib import Path

from coding_agent_ui.agent_core.agent import Agent
from coding_agent_ui.agent_core.loop import AgentLoop
from coding_agent_ui.agents.base.schemas import (
    AnalysisResult,
    EditResult,
    FileEdit,
    ImplementationPlan,
    ImplementationStep,
    PlanResult,
    TaskAnalysis,
)
from coding_agent_ui.agents.frontend.policy import FrontendPolicy
from coding_agent_ui.tools.fs import ReadFileTool
from coding_agent_ui.tools.registry import InMemoryToolRegistry
from tests.utils import QueueLLM, StubTool, dumps, make_settings


class ControlledWriteTool:
    """Write tool that can fail when restoring a specific file."""

    name = "write_file"

    def __init__(self, root: Path, original: dict[str, str], fail_restore_for: str) -> None:
        self._root = root
        self._original = original
        self._fail_restore_for = fail_restore_for

    def invoke(self, raw_input: dict) -> dict:
        path = raw_input["path"]
        content = raw_input["content"]
        full_path = (self._root / Path(path)).resolve()
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if path == self._fail_restore_for and content == self._original.get(path, ""):
            raise RuntimeError("simulated rollback failure")

        full_path.write_text(content, encoding="utf-8")
        return {"status": "ok"}


def _analysis_json() -> str:
    analysis = AnalysisResult(
        task_analysis=TaskAnalysis(intent="Rollback"),
        search_queries=[],
        focus_files=[],
    )
    return dumps(analysis)


def _plan_json(target_files: list[str]) -> str:
    plan = PlanResult(
        implementation_plan=ImplementationPlan(
            steps=[
                ImplementationStep(title="Edit files", details="Apply changes", files=target_files)
            ]
        ),
        target_files=target_files,
    )
    return dumps(plan)


def _edit_json(edits: list[FileEdit]) -> str:
    return dumps(EditResult(edits=edits))


def test_partial_rollback_failure_preserves_persisted_changes(tmp_path: Path) -> None:
    a_path = tmp_path / "src" / "a.js"
    b_path = tmp_path / "src" / "b.js"
    a_path.parent.mkdir(parents=True)
    a_path.write_text("const a = 1;\n", encoding="utf-8")
    b_path.write_text("const b = 1;\n", encoding="utf-8")

    edits = [
        FileEdit(
            path="src/a.js",
            content="const a = 2;\n",
            change_summary="Update a",
            rationale="Test change",
        ),
        FileEdit(
            path="src/b.js",
            content="const b = 2;\n",
            change_summary="Update b",
            rationale="Test change",
        ),
    ]

    original = {
        "src/a.js": "const a = 1;\n",
        "src/b.js": "const b = 1;\n",
    }

    tools = InMemoryToolRegistry()
    tools.register(StubTool("repo_inspect", lambda _: {"root": str(tmp_path), "tree": "repo/", "files": []}))
    tools.register(StubTool("code_search", lambda _: {"matches": []}))
    tools.register(ReadFileTool(root=str(tmp_path)))
    tools.register(ControlledWriteTool(tmp_path, original, "src/b.js"))
    tools.register(StubTool("run_lint", lambda _: {"exit_code": 1, "stdout": "", "stderr": "lint failed"}))
    tools.register(StubTool("run_tests", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))

    llm = QueueLLM([
        _analysis_json(),
        _plan_json(["src/a.js", "src/b.js"]),
        _edit_json(edits),
    ])

    agent = Agent(llm=llm, policy=FrontendPolicy(), tools=tools)
    settings = make_settings(lint_cmd="lint", max_iterations=1)
    loop = AgentLoop(agent, settings=settings, repo_root=str(tmp_path))

    report = loop.execute("Rollback", {})

    assert report.execution_status == "rolled_back"
    assert len(report.attempted_changes) == 2
    assert len(report.persisted_changes) == 1
    assert report.persisted_changes[0].path == "src/b.js"

    assert a_path.read_text(encoding="utf-8") == "const a = 1;\n"
    assert b_path.read_text(encoding="utf-8") == "const b = 2;\n"
