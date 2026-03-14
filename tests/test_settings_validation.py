"""Settings validation tests."""

from __future__ import annotations

import pytest

from coding_agent_ui.config.settings import Settings


def test_invalid_prompt_budgets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODING_AGENT_MAX_FILE_CONTEXT_CHARS_PER_FILE", "0")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_invalid_iteration_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODING_AGENT_MAX_ITERATIONS", "0")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_total_budget_less_than_per_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODING_AGENT_MAX_FILE_CONTEXT_CHARS_PER_FILE", "5000")
    monkeypatch.setenv("CODING_AGENT_MAX_TOTAL_FILE_CONTEXT_CHARS", "1000")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_invalid_preview_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODING_AGENT_PREVIEW_MODE", "invalid")
    with pytest.raises(ValueError):
        Settings.from_env()
