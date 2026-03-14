"""CLI entrypoint for the coding agent scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from coding_agent_ui.agent_core.agent import StructuredOutputError
from coding_agent_ui.agent_core.factory import create_frontend_agent
from coding_agent_ui.agent_core.loop import AgentLoop
from coding_agent_ui.agent_core.telemetry import configure_logging
from coding_agent_ui.config.settings import Settings
from coding_agent_ui.retrieval.context import DesignGuidanceContextBuilder
from coding_agent_ui.tools.fs import ReadFileTool, WriteFileTool
from coding_agent_ui.tools.accessibility import AccessibilityTool
from coding_agent_ui.tools.lint import LintTool
from coding_agent_ui.tools.preview import PreviewTool
from coding_agent_ui.tools.registry import InMemoryToolRegistry
from coding_agent_ui.tools.repo import RepoInspectTool
from coding_agent_ui.tools.search import CodeSearchTool
from coding_agent_ui.tools.test import TestTool


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Coding agent scaffold")
    parser.add_argument("--task", required=True, help="Task description for the agent")
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository root path (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; return proposed diffs only",
    )
    return parser


def main() -> None:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"Invalid settings: {exc}")
        raise SystemExit(2) from exc
    configure_logging(settings.log_level)

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"Repository root does not exist: {repo_root}")
        raise SystemExit(2)

    tools = InMemoryToolRegistry()
    tools.register(RepoInspectTool())
    tools.register(CodeSearchTool())
    tools.register(ReadFileTool(root=str(repo_root)))
    tools.register(WriteFileTool(root=str(repo_root)))
    tools.register(LintTool())
    tools.register(TestTool())
    tools.register(AccessibilityTool())
    tools.register(PreviewTool())

    context_builder = DesignGuidanceContextBuilder(repo_root=str(repo_root))
    context: Dict[str, Any] = context_builder.build(args.task)

    try:
        agent = create_frontend_agent(settings=settings, tools=tools)
    except Exception as exc:
        print(f"Initialization failed: {exc}")
        raise SystemExit(2) from exc

    loop = AgentLoop(agent, settings=settings, repo_root=str(repo_root), dry_run=args.dry_run)
    try:
        report = loop.execute(task=args.task, context=context)
    except StructuredOutputError as exc:
        error_payload = {
            "error": "structured_output_parse_failed",
            "details": exc.errors,
            "raw_output": exc.raw_output,
        }
        print(json.dumps(error_payload, indent=2))
        raise SystemExit(4) from exc

    print(json.dumps(report.model_dump(), indent=2))

    if report.validation_results.failures:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
