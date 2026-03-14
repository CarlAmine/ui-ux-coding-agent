# Coding Agent UI (LangChain v1)

This repository contains a production-minded v1 for a UI/UX-focused coding agent built on LangChain. The current implementation is intentionally minimal but functional, with emphasis on safe repo editing.

## v1 workflow

The agent executes a bounded, iterative loop:

1. Task analysis
2. Repository inspection
3. Code search
4. Implementation planning
5. Code editing
6. Lint/test validation
7. One optional revision if validation fails
8. Final structured report

## Execution status semantics

The final report includes an explicit `execution_status` field:

- `dry_run`: proposed changes only; no files were written.
- `applied`: changes were written and remain persisted.
- `rolled_back`: changes were attempted but reverted after validation failure.
- `no_changes`: no changes were proposed or applied.

The report distinguishes `attempted_changes` from `persisted_changes` to avoid ambiguity.

## Safety and determinism features

- Dry-run mode that never writes files and returns proposed diffs only.
- Automatic rollback if validation fails after the final attempt.
- Canonical, repo-relative path normalization to avoid duplicate references.
- Prompt budgets for repo tree, search results, and file context.

## Current capabilities

- Structured task analysis and implementation plan
- Repo inspection and basic code search
- Safe, bounded file editing (full-file replacement, no AST rewriting)
- Optional lint/test execution
- Optional accessibility and preview validation hooks (command-based)
- UI/UX specialization with explicit design criteria
- Design guidance ingestion from repo files
- Frontend evaluation scaffolding (tasks and rubric)

## Current limitations

- Single specialization (frontend UI/UX only)
- One revision max
- No advanced memory, retrieval index, or graph orchestration
- Preview hook is command-only; screenshot capture is not implemented yet
- Full-file replacement edits (no fine-grained patching)

## Configuration

Set environment variables to control the provider and runtime:

- `CODING_AGENT_LLM_PROVIDER` (default: `openai`)
- `CODING_AGENT_MODEL` (required for OpenAI provider)
- `CODING_AGENT_TEMPERATURE` (default: `0.2`)
- `CODING_AGENT_MAX_TOKENS` (optional)
- `CODING_AGENT_OPENAI_API_KEY` (optional, can also use `OPENAI_API_KEY`)
- `CODING_AGENT_OPENAI_BASE_URL` (optional)
- `CODING_AGENT_OPENAI_ORG` (optional)
- `CODING_AGENT_OPENAI_PROJECT` (optional)
- `CODING_AGENT_LINT_CMD` (optional, e.g. `npm run lint`)
- `CODING_AGENT_TEST_CMD` (optional, e.g. `npm test`)
- `CODING_AGENT_ACCESSIBILITY_CMD` or `CODING_AGENT_A11Y_CMD` (optional, e.g. `npm run a11y`)
- `CODING_AGENT_PREVIEW_CMD` (optional, e.g. `npm run preview:check`)
- `CODING_AGENT_PREVIEW_MODE` (optional, `command` or `screenshot`, default: `command`)

The `openai` provider uses the OpenAI Responses API via the `openai` Python SDK and requires `CODING_AGENT_MODEL` plus an API key.

If you want to run without an API key, set `CODING_AGENT_LLM_PROVIDER=mock` to use a safe, deterministic mock model that never calls external APIs.

Repo scanning controls:

- `CODING_AGENT_REPO_MAX_DEPTH` (default: `3`)
- `CODING_AGENT_REPO_MAX_FILES` (default: `500`)
- `CODING_AGENT_SEARCH_MAX_RESULTS` (default: `50`)
- `CODING_AGENT_EDIT_MAX_FILES` (default: `6`)
- `CODING_AGENT_MAX_ITERATIONS` (default: `2`)

Prompt budget controls:

- `CODING_AGENT_MAX_FILE_CONTEXT_CHARS_PER_FILE` (default: `6000`)
- `CODING_AGENT_MAX_TOTAL_FILE_CONTEXT_CHARS` (default: `18000`)
- `CODING_AGENT_MAX_REPO_TREE_CHARS` (default: `8000`)
- `CODING_AGENT_MAX_SEARCH_RESULT_CHARS` (default: `6000`)

## Dry-run behavior

Use `--dry-run` to avoid any file writes. The agent will return diffs based on proposed edits without modifying the repository. Validation is skipped in dry-run mode.

## Rollback behavior

If validation fails after the final attempt, the agent restores original file contents for all modified files. New files created during the run are deleted. The report will indicate `execution_status = rolled_back` and `persisted_changes` will be empty unless rollback fails.

## Proposed vs persisted changes

- `attempted_changes` are the diffs the agent tried to apply during the run.
- `persisted_changes` reflect the final repository state after rollback, if any.

## Frontend validation hooks

Validation runs can include:

- Lint (`CODING_AGENT_LINT_CMD`)
- Tests (`CODING_AGENT_TEST_CMD`)
- Accessibility checks (`CODING_AGENT_ACCESSIBILITY_CMD` or `CODING_AGENT_A11Y_CMD`)
- Preview/UI inspection (`CODING_AGENT_PREVIEW_CMD`)

Preview mode defaults to `command`. `screenshot` mode is defined but currently returns `unsupported` until a screenshot implementation is added.

## Tests

Test coverage focuses on core execution safety and reporting semantics:

- AgentLoop execution statuses (`dry_run`, `applied`, `rolled_back`, `no_changes`)
- Rollback restores existing files and deletes newly created files
- Settings validation for invalid budgets and limits
- Path normalization and search deduplication
- Structured output content extraction
- Structured output retry behavior
- Prompt budget truncation markers
- Partial rollback failure semantics

### Run tests locally

```bash
pip install -e .[dev]
pytest
```

## Design guidance files

If present at the repository root, these files are loaded into context:

- `design_principles.md`
- `ux_checklist.md`
- `component_guidelines.md`

## Local usage

```bash
export CODING_AGENT_LLM_PROVIDER=openai
export CODING_AGENT_MODEL=gpt-4o-mini
export CODING_AGENT_OPENAI_API_KEY=...  # or use OPENAI_API_KEY

coding-agent --task "Improve the settings page layout" --repo /path/to/repo
coding-agent --task "Improve the settings page layout" --repo /path/to/repo --dry-run
```

## Notes on stubs

Some components remain stubs and raise `NotImplementedError`, including the evaluation harness. These are clearly labeled in code and ready for incremental implementation.
