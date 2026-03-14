"""Tests for the OpenAI Responses adapter helpers."""

from __future__ import annotations

import json
import logging

import pytest

from coding_agent_ui.agent_core import llm as llm_mod
from coding_agent_ui.agent_core.llm import OpenAIResponsesChatModel


class DummyMessage:
    """Simple message stand-in for role mapping tests."""

    def __init__(self, role: str, content) -> None:  # noqa: ANN001
        self.type = role
        self.content = content


class FakeResponse:
    """Minimal OpenAI-like response payload."""

    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.id = "resp_test"


class FakeResponses:
    """Response endpoint shim that yields scripted outputs."""

    def __init__(self, scripted):  # noqa: ANN001
        self._scripted = list(scripted)
        self.calls = 0

    def create(self, **kwargs):  # noqa: ANN001
        self.calls += 1
        if not self._scripted:
            raise RuntimeError("No scripted responses left")
        item = self._scripted.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClient:
    """Client shim exposing responses.create."""

    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


class TransientError(Exception):
    """Simulated transient API error."""

    def __init__(self) -> None:
        super().__init__("transient")
        self.status_code = 429


class ConfigError(Exception):
    """Simulated 4xx configuration error."""

    def __init__(self) -> None:
        super().__init__("config")
        self.status_code = 400


def test_split_instructions_combines_system_messages() -> None:
    messages = [
        ("system", "alpha"),
        ("human", "hello"),
        ("system", "beta"),
        ("ai", "ok"),
    ]
    instructions, inputs = llm_mod._split_instructions(messages)

    assert instructions == "alpha\nbeta"
    assert inputs == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "ok"},
    ]


def test_split_instructions_no_system() -> None:
    instructions, inputs = llm_mod._split_instructions([("human", "hi")])
    assert instructions is None
    assert inputs == [{"role": "user", "content": "hi"}]


def test_role_mapping_and_stringification() -> None:
    assert llm_mod._normalize_role("human") == "user"
    assert llm_mod._normalize_role("ai") == "assistant"
    assert llm_mod._normalize_role("unknown") == "user"
    assert llm_mod._normalize_role(None) == "user"

    role, content = llm_mod._extract_role_content(DummyMessage("human", {"k": "v"}))
    assert role == "user"
    assert json.loads(content) == {"k": "v"}

    list_content = llm_mod._stringify_content([{"text": "alpha"}, {"content": "beta"}])
    assert list_content == "alpha\nbeta"


def test_retry_on_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = FakeResponses([TransientError(), FakeResponse("ok")])
    client = FakeClient(responses)
    model = OpenAIResponsesChatModel(
        client=client,
        model="gpt-test",
        temperature=0.1,
        max_output_tokens=None,
        logger=logging.getLogger("test"),
        retryable_exceptions=(TransientError,),
        max_retries=1,
    )

    monkeypatch.setattr(llm_mod.time, "sleep", lambda _: None)
    result = model._request_with_retry(None, [{"role": "user", "content": "hi"}])

    assert result == "ok"
    assert responses.calls == 2


def test_no_retry_on_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = FakeResponses([ConfigError()])
    client = FakeClient(responses)
    model = OpenAIResponsesChatModel(
        client=client,
        model="gpt-test",
        temperature=0.1,
        max_output_tokens=None,
        logger=logging.getLogger("test"),
        retryable_exceptions=(ConfigError,),
        max_retries=2,
    )

    monkeypatch.setattr(llm_mod.time, "sleep", lambda _: None)

    with pytest.raises(ConfigError):
        model._request_with_retry(None, [{"role": "user", "content": "hi"}])

    assert responses.calls == 1
