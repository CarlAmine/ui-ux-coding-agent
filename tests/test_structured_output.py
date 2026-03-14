"""Structured output extraction tests."""

from __future__ import annotations

import json

import pytest

from coding_agent_ui.agent_core.agent import Agent, StructuredOutputError
from coding_agent_ui.agent_core.policy import BasePolicy
from coding_agent_ui.tools.registry import InMemoryToolRegistry
from tests.utils import FakeResponse, QueueLLM
from pydantic import BaseModel


class DummyLLM:
    """LLM stub for Agent initialization."""

    def invoke(self, messages):  # noqa: ANN001, D401
        return FakeResponse("{}")


def _make_agent() -> Agent:
    return Agent(llm=DummyLLM(), policy=BasePolicy(), tools=InMemoryToolRegistry())


def test_extract_string_content() -> None:
    agent = _make_agent()
    response = FakeResponse("hello")
    assert agent._extract_content(response) == "hello"


def test_extract_dict_content() -> None:
    agent = _make_agent()
    response = FakeResponse({"key": "value"})
    extracted = agent._extract_content(response)
    assert json.loads(extracted) == {"key": "value"}


def test_extract_list_content() -> None:
    agent = _make_agent()
    response = FakeResponse([{"text": "alpha"}, {"content": "beta"}])
    extracted = agent._extract_content(response)
    assert extracted == "alpha\nbeta"


def test_structured_output_retry_succeeds() -> None:
    class ExampleSchema(BaseModel):
        value: str

    llm = QueueLLM([
        "not json",
        '{"value": "ok"}',
    ])
    agent = Agent(llm=llm, policy=BasePolicy(), tools=InMemoryToolRegistry())

    result = agent.invoke_structured(
        system_prompt="Return JSON.",
        user_prompt="Input: {input}",
        schema=ExampleSchema,
        variables={"input": "x"},
    )

    assert result.value == "ok"


def test_structured_output_error_after_retry() -> None:
    class ExampleSchema(BaseModel):
        value: str

    llm = QueueLLM(["bad", "still bad"])
    agent = Agent(llm=llm, policy=BasePolicy(), tools=InMemoryToolRegistry())

    with pytest.raises(StructuredOutputError):
        agent.invoke_structured(
            system_prompt="Return JSON.",
            user_prompt="Input: {input}",
            schema=ExampleSchema,
            variables={"input": "x"},
        )
