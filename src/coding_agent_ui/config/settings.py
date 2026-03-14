"""Environment-backed configuration for the coding agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _get_float(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default
    return float(value)


def _get_int(value: str | None, default: Optional[int]) -> Optional[int]:
    if value is None or value.strip() == "":
        return default
    return int(value)


def _get_str(value: str | None, default: Optional[str] = None) -> Optional[str]:
    if value is None or value.strip() == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    env: str
    log_level: str
    llm_provider: str
    model_name: str
    temperature: float
    max_tokens: Optional[int]
    openai_api_key: Optional[str]
    openai_base_url: Optional[str]
    openai_organization: Optional[str]
    openai_project: Optional[str]
    lint_cmd: Optional[str]
    test_cmd: Optional[str]
    accessibility_cmd: Optional[str]
    preview_cmd: Optional[str]
    preview_mode: str
    repo_max_depth: int
    repo_max_files: int
    search_max_results: int
    max_iterations: int
    edit_max_files: int
    max_diff_chars: int
    max_file_context_chars_per_file: int
    max_total_file_context_chars: int
    max_repo_tree_chars: int
    max_search_result_chars: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        openai_api_key = os.getenv("CODING_AGENT_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

        settings = cls(
            env=os.getenv("CODING_AGENT_ENV", "dev"),
            log_level=os.getenv("CODING_AGENT_LOG_LEVEL", "INFO"),
            llm_provider=os.getenv("CODING_AGENT_LLM_PROVIDER", "openai"),
            model_name=os.getenv("CODING_AGENT_MODEL", ""),
            temperature=_get_float(os.getenv("CODING_AGENT_TEMPERATURE"), 0.2),
            max_tokens=_get_int(os.getenv("CODING_AGENT_MAX_TOKENS"), None),
            openai_api_key=_get_str(openai_api_key),
            openai_base_url=_get_str(os.getenv("CODING_AGENT_OPENAI_BASE_URL")),
            openai_organization=_get_str(os.getenv("CODING_AGENT_OPENAI_ORG")),
            openai_project=_get_str(os.getenv("CODING_AGENT_OPENAI_PROJECT")),
            lint_cmd=_get_str(os.getenv("CODING_AGENT_LINT_CMD")),
            test_cmd=_get_str(os.getenv("CODING_AGENT_TEST_CMD")),
            accessibility_cmd=_get_str(
                os.getenv("CODING_AGENT_ACCESSIBILITY_CMD")
                or os.getenv("CODING_AGENT_A11Y_CMD")
            ),
            preview_cmd=_get_str(os.getenv("CODING_AGENT_PREVIEW_CMD")),
            preview_mode=os.getenv("CODING_AGENT_PREVIEW_MODE", "command"),
            repo_max_depth=int(os.getenv("CODING_AGENT_REPO_MAX_DEPTH", "3")),
            repo_max_files=int(os.getenv("CODING_AGENT_REPO_MAX_FILES", "500")),
            search_max_results=int(os.getenv("CODING_AGENT_SEARCH_MAX_RESULTS", "50")),
            max_iterations=int(os.getenv("CODING_AGENT_MAX_ITERATIONS", "2")),
            edit_max_files=int(os.getenv("CODING_AGENT_EDIT_MAX_FILES", "6")),
            max_diff_chars=int(os.getenv("CODING_AGENT_MAX_DIFF_CHARS", "4000")),
            max_file_context_chars_per_file=int(
                os.getenv("CODING_AGENT_MAX_FILE_CONTEXT_CHARS_PER_FILE", "6000")
            ),
            max_total_file_context_chars=int(
                os.getenv("CODING_AGENT_MAX_TOTAL_FILE_CONTEXT_CHARS", "18000")
            ),
            max_repo_tree_chars=int(os.getenv("CODING_AGENT_MAX_REPO_TREE_CHARS", "8000")),
            max_search_result_chars=int(
                os.getenv("CODING_AGENT_MAX_SEARCH_RESULT_CHARS", "6000")
            ),
        )

        _validate_settings(settings)
        return settings


def _validate_settings(settings: Settings) -> None:
    errors: list[str] = []

    if settings.repo_max_depth < 0:
        errors.append("CODING_AGENT_REPO_MAX_DEPTH must be >= 0")
    if settings.repo_max_files <= 0:
        errors.append("CODING_AGENT_REPO_MAX_FILES must be > 0")
    if settings.search_max_results <= 0:
        errors.append("CODING_AGENT_SEARCH_MAX_RESULTS must be > 0")
    if settings.max_iterations <= 0:
        errors.append("CODING_AGENT_MAX_ITERATIONS must be > 0")
    if settings.edit_max_files <= 0:
        errors.append("CODING_AGENT_EDIT_MAX_FILES must be > 0")
    if settings.max_diff_chars <= 0:
        errors.append("CODING_AGENT_MAX_DIFF_CHARS must be > 0")
    if settings.max_file_context_chars_per_file <= 0:
        errors.append("CODING_AGENT_MAX_FILE_CONTEXT_CHARS_PER_FILE must be > 0")
    if settings.max_total_file_context_chars <= 0:
        errors.append("CODING_AGENT_MAX_TOTAL_FILE_CONTEXT_CHARS must be > 0")
    if settings.max_repo_tree_chars <= 0:
        errors.append("CODING_AGENT_MAX_REPO_TREE_CHARS must be > 0")
    if settings.max_search_result_chars <= 0:
        errors.append("CODING_AGENT_MAX_SEARCH_RESULT_CHARS must be > 0")

    if settings.max_total_file_context_chars < settings.max_file_context_chars_per_file:
        errors.append(
            "CODING_AGENT_MAX_TOTAL_FILE_CONTEXT_CHARS must be >= CODING_AGENT_MAX_FILE_CONTEXT_CHARS_PER_FILE"
        )

    if settings.preview_mode not in {"command", "screenshot"}:
        errors.append("CODING_AGENT_PREVIEW_MODE must be 'command' or 'screenshot'")

    if errors:
        raise ValueError("Invalid settings: " + "; ".join(errors))
