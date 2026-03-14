"""Prompt budget truncation tests."""

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
        task_analysis=TaskAnalysis(intent="Check budgets"),
        search_queries=["foo"],
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


def test_prompt_budget_truncation_recorded(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "app.js"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("x" * 200, encoding="utf-8")

    tools = InMemoryToolRegistry()
    tools.register(
        StubTool(
            "repo_inspect",
            lambda _: {"root": str(tmp_path), "tree": "repo/" + ("x" * 50), "files": []},
        )
    )

    def search_handler(_: dict) -> dict:
        return {
            "matches": [
                {
                    "path": "src/app.js",
                    "line": 1,
                    "text": "y" * 100,
                }
            ]
        }

    tools.register(StubTool("code_search", search_handler))
    tools.register(ReadFileTool(root=str(tmp_path)))
    tools.register(WriteFileTool(root=str(tmp_path)))
    tools.register(StubTool("run_lint", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))
    tools.register(StubTool("run_tests", lambda _: {"exit_code": 0, "stdout": "", "stderr": ""}))

    llm = QueueLLM([
        _analysis_json(),
        _plan_json(["src/app.js"]),
        _edit_json([]),
    ])
    agent = Agent(llm=llm, policy=FrontendPolicy(), tools=tools)
    settings = make_settings(
        max_repo_tree_chars=10,
        max_search_result_chars=10,
        max_file_context_chars_per_file=10,
        max_total_file_context_chars=20,
    )

    loop = AgentLoop(agent, settings=settings, repo_root=str(tmp_path), dry_run=True)
    report = loop.execute("Check budgets", {})

    assert any("Repo tree truncated" in risk for risk in report.unresolved_risks)
    assert any("Search results truncated" in risk for risk in report.unresolved_risks)
    assert any("File context truncated" in risk for risk in report.unresolved_risks)
