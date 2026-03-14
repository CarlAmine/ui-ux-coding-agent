"""Prompt templates for the base coding agent."""

BASE_SYSTEM_PROMPT = (
    "You are a senior software engineer and coding agent. "
    "Return JSON only. Do not include markdown or extra commentary."
)

ANALYSIS_USER_PROMPT = (
    "Task: {task}\n"
    "Context: {context}\n"
    "Policy: {policy}\n\n"
    "Produce a task_analysis with intent, constraints, risks, and assumptions. "
    "Provide search_queries (short phrases) to find relevant code. "
    "Provide focus_files if the task hints at specific files.\n\n"
    "{format_instructions}\n"
    "Return JSON only."
)

PLAN_USER_PROMPT = (
    "Task: {task}\n"
    "Analysis: {analysis}\n"
    "Repo tree: {repo_tree}\n"
    "Search results: {search_results}\n"
    "Design guidance: {design_guidance}\n"
    "Policy: {policy}\n\n"
    "Produce an implementation_plan with concrete steps and files, "
    "and a target_files list of files to edit.\n\n"
    "{format_instructions}\n"
    "Return JSON only."
)

EDIT_USER_PROMPT = (
    "Task: {task}\n"
    "Plan: {plan}\n"
    "Design guidance: {design_guidance}\n"
    "Policy: {policy}\n\n"
    "Editing rules:\n"
    "- Make minimal diffs and preserve unrelated code.\n"
    "- Do not truncate files or remove code not mentioned.\n"
    "- Ensure syntactic validity and keep existing style.\n"
    "- Prefer existing components and tokens over new ones.\n\n"
    "File contents (path -> content):\n{file_context}\n\n"
    "Return edits with full updated file contents. "
    "Only include files that require changes.\n\n"
    "{format_instructions}\n"
    "Return JSON only."
)

REVISION_USER_PROMPT = (
    "Task: {task}\n"
    "Plan: {plan}\n"
    "Validation results: {validation_results}\n"
    "Design guidance: {design_guidance}\n"
    "Policy: {policy}\n\n"
    "Editing rules:\n"
    "- Make minimal diffs and preserve unrelated code.\n"
    "- Do not truncate files or remove code not mentioned.\n"
    "- Ensure syntactic validity and keep existing style.\n"
    "- Prefer existing components and tokens over new ones.\n\n"
    "File contents (path -> content):\n{file_context}\n\n"
    "Return edits with full updated file contents to fix validation issues. "
    "Only include files that need changes.\n\n"
    "{format_instructions}\n"
    "Return JSON only."
)
