"""LLM provider selection and validation tests."""

from __future__ import annotations

import pytest

from coding_agent_ui.agent_core.llm import LLMConfig, MockProvider, OpenAIProvider, get_provider


def _base_config(**overrides) -> LLMConfig:
    data = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": None,
        "api_key": "sk-test",
        "base_url": None,
        "organization": None,
        "project": None,
    }
    data.update(overrides)
    return LLMConfig(**data)


def test_get_provider_selection() -> None:
    assert isinstance(get_provider("mock"), MockProvider)
    assert isinstance(get_provider("openai"), OpenAIProvider)


def test_openai_provider_requires_model() -> None:
    config = _base_config(model="")
    with pytest.raises(ValueError):
        OpenAIProvider().create(config)


def test_openai_provider_requires_api_key() -> None:
    config = _base_config(api_key=None)
    with pytest.raises(ValueError):
        OpenAIProvider().create(config)


def test_openai_provider_rejects_invalid_base_url() -> None:
    config = _base_config(base_url="ftp://example.com")
    with pytest.raises(ValueError):
        OpenAIProvider().create(config)
