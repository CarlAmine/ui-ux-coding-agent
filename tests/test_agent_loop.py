"""AgentLoop behavior tests."""

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
from coding_agent_ui.tools.fs import ReadFileTool, WriteFileTool
from coding_agent_ui.tools.registry import InMemoryToolRegistry
from tests.utils import QueueLLM, StubTool, dumps, make_settings


def _analysis_json() -> str:
    analysis = AnalysisResult(
        task_analysis=TaskAnalysis(intent="Update UI"),
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


def _build_agent_loop(tmp_path: Path, llm_responses: list[str], settings_overrides: dict) -> AgentLoop:
    tools = InMemoryToolRegistry()
    tools.register(StubTool("repo_inspect", lambda _: {"root": str(tmp_path), "tree": "repo/", "files": []}))
    tools.register(StubTool("code_search", lambda _: {"matches": []}))
    tools.register(ReadFileTool(root=str(tmp_path)))
    tools.register(WriteFileTool(root=str(tmp_path)))
    tools.register(StubTool("run_lint", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))
    tools.register(StubTool("run_tests", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))

    llm = QueueLLM(llm_responses)
    agent = Agent(llm=llm, policy=FrontendPolicy(), tools=tools)
    dry_run = bool(settings_overrides.pop("dry_run", False))
    settings = make_settings(**settings_overrides)
    return AgentLoop(agent, settings=settings, repo_root=str(tmp_path), dry_run=dry_run)


def test_dry_run_status_and_changes(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "app.js"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("const a = 1;\n", encoding="utf-8")

    edits = [
        FileEdit(
            path="src/app.js",
            content="const a = 2;\n",
            change_summary="Update value",
            rationale="Test change",
        )
    ]

    loop = _build_agent_loop(
        tmp_path,
        [_analysis_json(), _plan_json(["src/app.js"]), _edit_json(edits)],
        {"dry_run": True},
    )
    report = loop.execute("Update value", {})

    assert report.execution_status == "dry_run"
    assert len(report.attempted_changes) == 1
    assert report.persisted_changes == []
    assert file_path.read_text(encoding="utf-8") == "const a = 1;\n"


def test_no_changes_status(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "app.js"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("const a = 1;\n", encoding="utf-8")

    loop = _build_agent_loop(
        tmp_path,
        [_analysis_json(), _plan_json(["src/app.js"]), _edit_json([])],
        {},
    )
    report = loop.execute("No changes", {})

    assert report.execution_status == "no_changes"
    assert report.attempted_changes == []
    assert report.persisted_changes == []


def test_applied_status(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "app.js"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("const a = 1;\n", encoding="utf-8")

    edits = [
        FileEdit(
            path="src/app.js",
            content="const a = 2;\n",
            change_summary="Update value",
            rationale="Test change",
        )
    ]

    loop = _build_agent_loop(
        tmp_path,
        [_analysis_json(), _plan_json(["src/app.js"]), _edit_json(edits)],
        {},
    )
    report = loop.execute("Apply change", {})

    assert report.execution_status == "applied"
    assert len(report.persisted_changes) == 1
    assert file_path.read_text(encoding="utf-8") == "const a = 2;\n"


def test_rollback_restores_and_deletes(tmp_path: Path) -> None:
    existing_path = tmp_path / "src" / "app.js"
    existing_path.parent.mkdir(parents=True)
    existing_path.write_text("const a = 1;\n", encoding="utf-8")

    new_path = tmp_path / "src" / "new.js"

    edits = [
        FileEdit(
            path="src/app.js",
            content="const a = 2;\n",
            change_summary="Update value",
            rationale="Test change",
        ),
        FileEdit(
            path="src/new.js",
            content="const b = 1;\n",
            change_summary="Add file",
            rationale="Test new file",
        ),
    ]

    loop = _build_agent_loop(
        tmp_path,
        [_analysis_json(), _plan_json(["src/app.js", "src/new.js"]), _edit_json(edits)],
        {"lint_cmd": "lint", "max_iterations": 1},
    )

    # Override lint tool to force failure.
    loop._agent.tools.get("run_lint").invoke = lambda _: {
        "exit_code": 1,
        "stdout": "",
        "stderr": "lint failed",
    }

    report = loop.execute("Rollback", {})

    assert report.execution_status == "rolled_back"
    assert report.persisted_changes == []
    assert len(report.attempted_changes) == 2
    assert existing_path.read_text(encoding="utf-8") == "const a = 1;\n"
    assert not new_path.exists()
