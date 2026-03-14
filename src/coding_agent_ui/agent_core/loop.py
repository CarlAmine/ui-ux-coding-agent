"""Iterative agent workflow loop."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from coding_agent_ui.agent_core.agent import Agent
from coding_agent_ui.agents.base.prompts import (
    ANALYSIS_USER_PROMPT,
    EDIT_USER_PROMPT,
    PLAN_USER_PROMPT,
    REVISION_USER_PROMPT,
    BASE_SYSTEM_PROMPT,
)
from coding_agent_ui.agents.base.schemas import (
    AgentReport,
    AnalysisResult,
    EditResult,
    ExecutionStatus,
    FileChange,
    PlanResult,
    ValidationResults,
    ValidationRun,
)
from coding_agent_ui.agents.frontend.prompts import FRONTEND_SYSTEM_PROMPT
from coding_agent_ui.config.settings import Settings
from coding_agent_ui.tools.command import CommandOutput, parse_command
from coding_agent_ui.tools.fs import ReadFileOutput, WriteFileOutput
from coding_agent_ui.tools.preview import PreviewOutput
from coding_agent_ui.tools.repo import RepoInspectOutput
from coding_agent_ui.tools.search import CodeSearchOutput


class AgentLoop:
    """Iterative agent loop for analysis, planning, editing, and validation."""

    def __init__(self, agent: Agent, settings: Settings, repo_root: str, dry_run: bool = False) -> None:
        self._agent = agent
        self._settings = settings
        self._repo_root = Path(repo_root).resolve()
        self._system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{FRONTEND_SYSTEM_PROMPT}"
        self._dry_run = dry_run

    def execute(self, task: str, context: Dict[str, Any]) -> AgentReport:
        """Execute the end-to-end workflow and return a structured report."""
        unresolved: List[str] = []
        rollback_performed = False

        analysis = self._run_analysis(task, context)
        repo_info = self._inspect_repo()
        search_results = self._search_repo(task, analysis)
        plan = self._run_plan(task, analysis, repo_info, search_results, context, unresolved)

        target_files = self._select_target_files(plan, analysis, search_results, unresolved)
        file_context, original_contents, original_exists = self._load_file_context(
            target_files, unresolved
        )

        edits = self._run_edit(task, plan, context, file_context, unresolved)
        attempted_contents, metadata, modified_paths, original_exists = self._apply_edits(
            edits,
            original_contents,
            original_exists,
            unresolved,
            dry_run=self._dry_run,
        )
        file_context = dict(attempted_contents)

        if self._dry_run:
            unresolved.append("Dry-run enabled; no files were written.")
            validation = ValidationResults(skipped=["lint", "tests", "accessibility", "preview", "dry-run"])
            attempted_changes = self._build_file_changes(original_contents, attempted_contents, metadata)
            persisted_changes: List[FileChange] = []
            execution_status = self._derive_status(
                attempted_changes=attempted_changes,
                persisted_changes=persisted_changes,
                rollback_performed=False,
                dry_run=True,
            )
            final_summary = self._build_summary(
                execution_status, attempted_changes, persisted_changes, validation
            )
            if not attempted_changes:
                unresolved.append("No file changes were proposed.")
            return AgentReport(
                execution_status=execution_status,
                task_analysis=analysis.task_analysis,
                implementation_plan=plan.implementation_plan,
                attempted_changes=attempted_changes,
                persisted_changes=persisted_changes,
                validation_results=validation,
                final_summary=final_summary,
                unresolved_risks=unresolved,
            )

        validation = self._run_validation(unresolved)
        if validation.failures and self._settings.max_iterations > 1:
            revision = self._run_revision(task, plan, context, file_context, validation, unresolved)
            attempted_contents, metadata, modified_paths, original_exists = self._apply_edits(
                revision,
                original_contents,
                original_exists,
                unresolved,
                metadata=metadata,
                dry_run=False,
            )
            file_context = dict(attempted_contents)
            validation = self._run_validation(unresolved)

        persisted_contents = dict(attempted_contents)
        if validation.failures:
            persisted_contents, rollback_performed = self._rollback_changes(
                original_contents, original_exists, modified_paths, persisted_contents, unresolved
            )

        attempted_changes = self._build_file_changes(original_contents, attempted_contents, metadata)
        persisted_changes = self._build_file_changes(original_contents, persisted_contents, metadata)
        execution_status = self._derive_status(
            attempted_changes=attempted_changes,
            persisted_changes=persisted_changes,
            rollback_performed=rollback_performed,
            dry_run=False,
        )
        final_summary = self._build_summary(
            execution_status, attempted_changes, persisted_changes, validation
        )

        unresolved.extend(analysis.task_analysis.risks)
        if validation.failures:
            unresolved.append("Validation failures remain: " + ", ".join(validation.failures))
        if rollback_performed:
            unresolved.append("Rollback performed; repository restored to original state.")
        if not attempted_changes:
            unresolved.append("No file changes were proposed.")

        return AgentReport(
            execution_status=execution_status,
            task_analysis=analysis.task_analysis,
            implementation_plan=plan.implementation_plan,
            attempted_changes=attempted_changes,
            persisted_changes=persisted_changes,
            validation_results=validation,
            final_summary=final_summary,
            unresolved_risks=unresolved,
        )

    def _run_analysis(self, task: str, context: Dict[str, Any]) -> AnalysisResult:
        return self._agent.invoke_structured(
            system_prompt=self._system_prompt,
            user_prompt=ANALYSIS_USER_PROMPT,
            schema=AnalysisResult,
            variables={
                "task": task,
                "context": context,
                "policy": self._agent.policy.rules(),
            },
        )

    def _inspect_repo(self) -> RepoInspectOutput:
        tool = self._agent.tools.get("repo_inspect")
        raw = tool.invoke(
            {
                "path": str(self._repo_root),
                "max_depth": self._settings.repo_max_depth,
                "max_files": self._settings.repo_max_files,
            }
        )
        return RepoInspectOutput.model_validate(raw)

    def _search_repo(self, task: str, analysis: AnalysisResult) -> CodeSearchOutput:
        tool = self._agent.tools.get("code_search")
        queries = analysis.search_queries or self._fallback_search_queries(task)
        matches: List[Dict[str, Any]] = []
        seen = set()

        for query in queries:
            raw = tool.invoke(
                {
                    "query": query,
                    "path": str(self._repo_root),
                    "max_results": self._settings.search_max_results,
                }
            )
            result = CodeSearchOutput.model_validate(raw)
            for match in result.matches:
                normalized_path = self._normalize_path(match.path)
                if normalized_path is None:
                    continue
                key = (normalized_path, match.line, match.text)
                if key in seen:
                    continue
                seen.add(key)
                matches.append(
                    {
                        "path": normalized_path,
                        "line": match.line,
                        "text": match.text,
                    }
                )
                if len(matches) >= self._settings.search_max_results:
                    break
            if len(matches) >= self._settings.search_max_results:
                break

        return CodeSearchOutput.model_validate({"matches": matches})

    def _run_plan(
        self,
        task: str,
        analysis: AnalysisResult,
        repo_info: RepoInspectOutput,
        search_results: CodeSearchOutput,
        context: Dict[str, Any],
        unresolved: List[str],
    ) -> PlanResult:
        return self._agent.invoke_structured(
            system_prompt=self._system_prompt,
            user_prompt=PLAN_USER_PROMPT,
            schema=PlanResult,
            variables={
                "task": task,
                "analysis": analysis.model_dump(),
                "repo_tree": self._format_repo_tree(repo_info.tree, unresolved),
                "search_results": self._format_search_results(search_results, unresolved),
                "design_guidance": context.get("design_guidance", {}),
                "policy": self._agent.policy.rules(),
            },
        )

    def _run_edit(
        self,
        task: str,
        plan: PlanResult,
        context: Dict[str, Any],
        file_context: Dict[str, str],
        unresolved: List[str],
    ) -> EditResult:
        return self._agent.invoke_structured(
            system_prompt=self._system_prompt,
            user_prompt=EDIT_USER_PROMPT,
            schema=EditResult,
            variables={
                "task": task,
                "plan": plan.model_dump(),
                "design_guidance": context.get("design_guidance", {}),
                "policy": self._agent.policy.rules(),
                "file_context": self._format_file_context(file_context, unresolved),
            },
        )

    def _run_revision(
        self,
        task: str,
        plan: PlanResult,
        context: Dict[str, Any],
        file_context: Dict[str, str],
        validation: ValidationResults,
        unresolved: List[str],
    ) -> EditResult:
        return self._agent.invoke_structured(
            system_prompt=self._system_prompt,
            user_prompt=REVISION_USER_PROMPT,
            schema=EditResult,
            variables={
                "task": task,
                "plan": plan.model_dump(),
                "validation_results": validation.model_dump(),
                "design_guidance": context.get("design_guidance", {}),
                "policy": self._agent.policy.rules(),
                "file_context": self._format_file_context(file_context, unresolved),
            },
        )

    def _select_target_files(
        self,
        plan: PlanResult,
        analysis: AnalysisResult,
        search_results: CodeSearchOutput,
        unresolved: List[str],
    ) -> List[str]:
        candidates = []
        candidates.extend(plan.target_files)
        candidates.extend(analysis.focus_files)
        candidates.extend(self._files_from_search(search_results))

        normalized: List[str] = []
        for path in candidates:
            normalized_path = self._normalize_path(path)
            if normalized_path is None:
                unresolved.append(f"Skipped path outside repo root: {path}")
                continue
            if normalized_path not in normalized:
                normalized.append(normalized_path)

        if len(normalized) > self._settings.edit_max_files:
            unresolved.append(
                f"Target files exceeded limit ({self._settings.edit_max_files}); truncating list."
            )
            normalized = normalized[: self._settings.edit_max_files]

        return normalized

    def _load_file_context(
        self, target_files: Iterable[str], unresolved: List[str]
    ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, bool]]:
        read_tool = self._agent.tools.get("read_file")
        file_context: Dict[str, str] = {}
        original_contents: Dict[str, str] = {}
        original_exists: Dict[str, bool] = {}

        for path in target_files:
            try:
                raw = read_tool.invoke({"path": path})
                result = ReadFileOutput.model_validate(raw)
                file_context[path] = result.content
                original_contents[path] = result.content
                original_exists[path] = True
            except FileNotFoundError:
                original_contents[path] = ""
                original_exists[path] = False
                unresolved.append(f"File not found: {path}")
            except Exception as exc:
                unresolved.append(f"Failed to read {path}: {exc}")

        return file_context, original_contents, original_exists

    def _apply_edits(
        self,
        edits: EditResult,
        original_contents: Dict[str, str],
        original_exists: Dict[str, bool],
        unresolved: List[str],
        metadata: Dict[str, Tuple[str, str]] | None = None,
        dry_run: bool = False,
    ) -> Tuple[Dict[str, str], Dict[str, Tuple[str, str]], List[str], Dict[str, bool]]:
        write_tool = self._agent.tools.get("write_file")
        read_tool = self._agent.tools.get("read_file")
        current_contents = dict(original_contents)
        metadata = metadata or {}
        modified_paths: List[str] = []

        for edit in edits.edits:
            normalized_path = self._normalize_path(edit.path)
            if normalized_path is None:
                unresolved.append(f"Skipped edit outside repo root: {edit.path}")
                continue

            if normalized_path not in original_contents:
                try:
                    raw = read_tool.invoke({"path": normalized_path})
                    result = ReadFileOutput.model_validate(raw)
                    original_contents[normalized_path] = result.content
                    original_exists[normalized_path] = True
                    current_contents[normalized_path] = result.content
                except FileNotFoundError:
                    original_contents[normalized_path] = ""
                    original_exists[normalized_path] = False
                except Exception as exc:
                    unresolved.append(f"Failed to read {normalized_path}: {exc}")
                    continue

            if not dry_run:
                try:
                    raw = write_tool.invoke(
                        {"path": normalized_path, "content": edit.content, "overwrite": True}
                    )
                    WriteFileOutput.model_validate(raw)
                except Exception as exc:
                    unresolved.append(f"Failed to write {normalized_path}: {exc}")
                    continue

            current_contents[normalized_path] = edit.content
            metadata[normalized_path] = (edit.change_summary, edit.rationale)
            if normalized_path not in modified_paths:
                modified_paths.append(normalized_path)

        return current_contents, metadata, modified_paths, original_exists

    def _rollback_changes(
        self,
        original_contents: Dict[str, str],
        original_exists: Dict[str, bool],
        modified_paths: Iterable[str],
        persisted_contents: Dict[str, str],
        unresolved: List[str],
    ) -> Tuple[Dict[str, str], bool]:
        write_tool = self._agent.tools.get("write_file")
        performed = False

        for path in modified_paths:
            if not self._is_within_root(path):
                unresolved.append(f"Rollback skipped outside repo root: {path}")
                continue

            existed = original_exists.get(path, True)
            if not existed:
                try:
                    full_path = (self._repo_root / Path(path)).resolve()
                    if full_path.exists():
                        full_path.unlink()
                        performed = True
                    persisted_contents.pop(path, None)
                except Exception as exc:
                    unresolved.append(f"Failed to delete {path} during rollback: {exc}")
                continue

            try:
                raw = write_tool.invoke({"path": path, "content": original_contents.get(path, "")})
                WriteFileOutput.model_validate(raw)
                persisted_contents[path] = original_contents.get(path, "")
                performed = True
            except Exception as exc:
                unresolved.append(f"Failed to restore {path} during rollback: {exc}")

        return persisted_contents, performed

    def _run_validation(self, unresolved: List[str] | None = None) -> ValidationResults:
        runs: List[ValidationRun] = []
        failures: List[str] = []
        skipped: List[str] = []
        notes: List[str] = []

        lint_cmd = self._settings.lint_cmd
        test_cmd = self._settings.test_cmd
        accessibility_cmd = self._settings.accessibility_cmd
        preview_cmd = self._settings.preview_cmd

        if lint_cmd:
            runs.append(self._execute_command("lint", lint_cmd))
            if runs[-1].exit_code != 0:
                failures.append("lint")
        else:
            skipped.append("lint")

        if test_cmd:
            runs.append(self._execute_command("tests", test_cmd))
            if runs[-1].exit_code != 0:
                failures.append("tests")
        else:
            skipped.append("tests")

        if accessibility_cmd:
            runs.append(self._execute_command("accessibility", accessibility_cmd))
            if runs[-1].exit_code != 0:
                failures.append("accessibility")
        else:
            skipped.append("accessibility")

        if preview_cmd:
            preview_run, preview_status, preview_note = self._execute_preview(preview_cmd)
            if preview_status == "unsupported":
                skipped.append("preview")
                if preview_note:
                    notes.append(preview_note)
            else:
                runs.append(preview_run)
                if preview_run.exit_code != 0:
                    failures.append("preview")
        else:
            skipped.append("preview")

        if unresolved is not None:
            unresolved.extend(notes)

        return ValidationResults(runs=runs, skipped=skipped, failures=failures)

    def _execute_command(self, name: str, command: str) -> ValidationRun:
        tool_map = {
            "lint": "run_lint",
            "tests": "run_tests",
            "accessibility": "run_accessibility",
        }
        tool_name = tool_map.get(name)
        if tool_name is None:
            raise ValueError(f"Unsupported validation command: {name}")
        tool = self._agent.tools.get(tool_name)
        cmd = parse_command(command)
        raw = tool.invoke({"cmd": cmd, "cwd": str(self._repo_root)})
        output = CommandOutput.model_validate(raw)
        return ValidationRun(
            name=name,
            command=cmd,
            exit_code=output.exit_code,
            stdout=output.stdout,
            stderr=output.stderr,
        )

    def _execute_preview(self, command: str) -> tuple[ValidationRun, str, str | None]:
        tool = self._agent.tools.get("run_preview")
        cmd = parse_command(command)
        raw = tool.invoke(
            {
                "cmd": cmd,
                "cwd": str(self._repo_root),
                "mode": self._settings.preview_mode,
            }
        )
        output = PreviewOutput.model_validate(raw)

        if output.status == "unsupported":
            return (
                ValidationRun(
                    name="preview",
                    command=cmd,
                    exit_code=0,
                    stdout=output.stdout,
                    stderr=output.stderr,
                    artifacts=output.artifacts,
                ),
                "unsupported",
                output.note,
            )

        return (
            ValidationRun(
                name="preview",
                command=cmd,
                exit_code=output.exit_code or 1,
                stdout=output.stdout,
                stderr=output.stderr,
                artifacts=output.artifacts,
            ),
            output.status,
            output.note,
        )

    def _build_file_changes(
        self,
        original: Dict[str, str],
        current: Dict[str, str],
        metadata: Dict[str, Tuple[str, str]],
    ) -> List[FileChange]:
        changes: List[FileChange] = []

        for path, new_content in current.items():
            old_content = original.get(path, "")
            if new_content == old_content:
                continue

            diff = "\n".join(
                difflib.unified_diff(
                    old_content.splitlines(),
                    new_content.splitlines(),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            if len(diff) > self._settings.max_diff_chars:
                diff = diff[: self._settings.max_diff_chars] + "\n... (truncated)"

            summary, rationale = metadata.get(path, ("Updated file", "No rationale provided"))
            changes.append(
                FileChange(
                    path=path,
                    change_summary=summary,
                    rationale=rationale,
                    diff=diff,
                )
            )

        return changes

    def _derive_status(
        self,
        *,
        attempted_changes: List[FileChange],
        persisted_changes: List[FileChange],
        rollback_performed: bool,
        dry_run: bool,
    ) -> ExecutionStatus:
        if not attempted_changes:
            return "no_changes"
        if dry_run:
            return "dry_run"
        if rollback_performed:
            return "rolled_back"
        if persisted_changes:
            return "applied"
        return "no_changes"

    def _build_summary(
        self,
        status: ExecutionStatus,
        attempted_changes: List[FileChange],
        persisted_changes: List[FileChange],
        validation: ValidationResults,
    ) -> str:
        if status == "no_changes":
            return "No code changes were proposed."
        if status == "dry_run":
            return f"Dry-run: proposed {len(attempted_changes)} change(s); no files written."
        if status == "rolled_back":
            return (
                f"Attempted {len(attempted_changes)} change(s) but rolled back; "
                "repository restored."
            )
        if status == "applied":
            if validation.failures:
                return (
                    f"Applied {len(persisted_changes)} change(s), but validation failed."
                )
            return f"Applied {len(persisted_changes)} change(s)."
        return "Execution completed."

    def _format_repo_tree(self, repo_tree: str, unresolved: List[str]) -> str:
        if len(repo_tree) <= self._settings.max_repo_tree_chars:
            return repo_tree
        unresolved.append("Repo tree truncated for prompt budget.")
        return repo_tree[: self._settings.max_repo_tree_chars] + "\n... (truncated)"

    def _format_search_results(self, search_results: CodeSearchOutput, unresolved: List[str]) -> str:
        if not search_results.matches:
            return "No matches."

        lines = []
        for match in search_results.matches:
            lines.append(f"{match.path}:{match.line}: {match.text}")
        joined = "\n".join(lines)

        if len(joined) > self._settings.max_search_result_chars:
            unresolved.append("Search results truncated for prompt budget.")
            return joined[: self._settings.max_search_result_chars] + "\n... (truncated)"
        return joined

    def _format_file_context(self, file_context: Dict[str, str], unresolved: List[str]) -> str:
        if not file_context:
            return "No file context available."

        sections = []
        total_chars = 0
        total_budget = self._settings.max_total_file_context_chars
        per_file_budget = self._settings.max_file_context_chars_per_file

        for path, content in file_context.items():
            normalized_path = self._normalize_path(path) or path
            truncated_content = content
            if len(truncated_content) > per_file_budget:
                truncated_content = truncated_content[:per_file_budget] + "\n... (truncated)"
                unresolved.append(f"File context truncated for {normalized_path}.")

            section = f"--- {normalized_path} ---\n{truncated_content}"
            if total_chars + len(section) > total_budget:
                remaining = max(total_budget - total_chars, 0)
                if remaining == 0:
                    unresolved.append("Total file context budget exceeded; remaining files omitted.")
                    break
                section = section[:remaining] + "\n... (truncated)"
                unresolved.append("Total file context budget truncated.")
                sections.append(section)
                break

            sections.append(section)
            total_chars += len(section)

        return "\n\n".join(sections)

    def _files_from_search(self, search_results: CodeSearchOutput) -> List[str]:
        files = []
        for match in search_results.matches:
            if match.path not in files:
                files.append(match.path)
        return files

    def _fallback_search_queries(self, task: str) -> List[str]:
        tokens = re.findall(r"[a-zA-Z0-9_]+", task.lower())
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "into",
            "that",
            "this",
            "page",
            "screen",
            "feature",
            "update",
            "improve",
            "fix",
        }
        keywords = [t for t in tokens if t not in stopwords and len(t) > 2]
        unique = []
        for token in keywords:
            if token not in unique:
                unique.append(token)
        return unique[:5]

    def _normalize_path(self, path: str) -> str | None:
        if not path:
            return None
        candidate = Path(path)
        resolved = candidate if candidate.is_absolute() else self._repo_root / candidate
        resolved = resolved.resolve()
        if resolved == self._repo_root or self._repo_root in resolved.parents:
            return resolved.relative_to(self._repo_root).as_posix()
        return None

    def _is_within_root(self, path: str) -> bool:
        candidate = Path(path)
        resolved = candidate if candidate.is_absolute() else self._repo_root / candidate
        resolved = resolved.resolve()
        return resolved == self._repo_root or self._repo_root in resolved.parents
