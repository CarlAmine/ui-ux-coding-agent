"""LLM provider abstraction and factory helpers."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from coding_agent_ui.agent_core.telemetry import get_logger


@dataclass(frozen=True)
class LLMConfig:
    """Configuration required to build an LLM client."""

    provider: str
    model: str
    temperature: float
    max_tokens: Optional[int]
    api_key: Optional[str]
    base_url: Optional[str]
    organization: Optional[str]
    project: Optional[str]


class LLMProvider(Protocol):
    """LLM provider interface."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        """Return a configured LangChain chat model."""
        ...


class StubProvider:
    """Stub provider that raises a clear error."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        _ = config
        raise NotImplementedError(
            "No LLM provider configured. Set CODING_AGENT_LLM_PROVIDER and model settings."
        )


class MockResponse:
    """Minimal response wrapper for the mock provider."""

    def __init__(self, content: str) -> None:
        self.content = content


class MockChatModel:
    """Mock LLM that returns safe, deterministic JSON outputs."""

    def invoke(self, messages):  # noqa: ANN001
        text = "\n".join(
            str(getattr(message, "content", message)) for message in messages
        )

        if "task_analysis" in text and "implementation_plan" not in text:
            payload = {
                "task_analysis": {
                    "intent": "Mock analysis",
                    "constraints": [],
                    "risks": [],
                    "assumptions": [],
                },
                "search_queries": [],
                "focus_files": [],
            }
            return MockResponse(json.dumps(payload))

        if "implementation_plan" in text:
            payload = {"implementation_plan": {"steps": []}, "target_files": []}
            return MockResponse(json.dumps(payload))

        if "Return edits" in text:
            payload = {"edits": []}
            return MockResponse(json.dumps(payload))

        return MockResponse("{}")


class MockProvider:
    """Mock provider for local runs without an API key."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        _ = config
        return MockChatModel()


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _normalize_role(role: Optional[str]) -> str:
    if role is None:
        return "user"
    mapping = {
        "human": "user",
        "user": "user",
        "ai": "assistant",
        "assistant": "assistant",
        "system": "system",
        "tool": "tool",
    }
    return mapping.get(role, "user")


def _extract_role_content(message: Any) -> tuple[str, str]:
    if isinstance(message, tuple) and len(message) == 2:
        role, content = message
        return _normalize_role(str(role)), _stringify_content(content)
    role = getattr(message, "type", None) or getattr(message, "role", None)
    content = getattr(message, "content", message)
    return _normalize_role(str(role) if role is not None else None), _stringify_content(content)


def _split_instructions(messages: Sequence[Any]) -> tuple[Optional[str], list[dict[str, str]]]:
    instructions_parts: list[str] = []
    inputs: list[dict[str, str]] = []
    for message in messages:
        role, content = _extract_role_content(message)
        if role == "system":
            if content:
                instructions_parts.append(content)
            continue
        inputs.append({"role": role, "content": content})
    instructions = "\n".join(instructions_parts).strip()
    return (instructions or None), inputs


class OpenAIResponsesChatModel(BaseChatModel):
    """LangChain chat model backed by the OpenAI Responses API."""

    client: Any = Field(exclude=True)
    model: str
    temperature: float = 0.2
    max_output_tokens: Optional[int] = None
    logger: Any = Field(exclude=True)
    retryable_exceptions: tuple[type[BaseException], ...] = Field(
        default_factory=tuple,
        exclude=True,
    )
    max_retries: int = 2

    @property
    def _llm_type(self) -> str:
        return "openai-responses"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if stop:
            self.logger.debug("Stop tokens ignored for OpenAI Responses API.")
        instructions, input_messages = _split_instructions(messages)
        output_text = self._request_with_retry(instructions, input_messages)
        ai_message = AIMessage(content=output_text)
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def _request_with_retry(
        self,
        instructions: Optional[str],
        input_messages: list[dict[str, str]],
    ) -> str:
        delay = 1.0
        last_exception: Optional[BaseException] = None

        for attempt in range(self.max_retries + 1):
            try:
                payload: dict[str, Any] = {
                    "model": self.model,
                    "input": input_messages,
                    "temperature": self.temperature,
                }
                if instructions:
                    payload["instructions"] = instructions
                if self.max_output_tokens is not None:
                    payload["max_output_tokens"] = self.max_output_tokens

                self.logger.debug(
                    "OpenAI request model=%s messages=%d",
                    self.model,
                    len(input_messages),
                )
                response = self.client.responses.create(**payload)
                output_text = getattr(response, "output_text", "")
                if not isinstance(output_text, str):
                    output_text = str(output_text)
                self.logger.debug(
                    "OpenAI response id=%s output_chars=%d",
                    getattr(response, "id", "unknown"),
                    len(output_text),
                )
                return output_text
            except self.retryable_exceptions as exc:  # type: ignore[misc]
                last_exception = exc
                status_code = getattr(exc, "status_code", None)
                if status_code is not None and status_code < 500 and status_code != 429:
                    raise
                if attempt >= self.max_retries:
                    raise
                wait = delay * (1 + random.random() * 0.2)
                self.logger.warning(
                    "OpenAI transient error (attempt %d/%d), retrying in %.2fs: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    wait,
                    exc,
                )
                time.sleep(wait)
                delay *= 2
            except Exception as exc:  # noqa: BLE001
                last_exception = exc
                raise

        if last_exception:
            raise last_exception
        raise RuntimeError("OpenAI request failed after retries.")


class OpenAIProvider:
    """OpenAI provider adapter using the Responses API."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        if not config.model:
            raise ValueError("OpenAI provider requires CODING_AGENT_MODEL to be set.")
        api_key = (config.api_key or "").strip()
        if not api_key:
            raise ValueError(
                "OpenAI provider requires CODING_AGENT_OPENAI_API_KEY or OPENAI_API_KEY to be set."
            )
        base_url = config.base_url.strip() if config.base_url else None
        if base_url and not base_url.startswith(("http://", "https://")):
            raise ValueError("CODING_AGENT_OPENAI_BASE_URL must start with http:// or https://")

        try:
            from openai import OpenAI
            import openai
        except ImportError as exc:
            raise ImportError(
                "openai is required for the OpenAI provider. Install it with: pip install openai"
            ) from exc

        retryable = tuple(
            exc
            for exc_name in (
                "RateLimitError",
                "APITimeoutError",
                "APIConnectionError",
                "InternalServerError",
                "APIStatusError",
            )
            if (exc := getattr(openai, exc_name, None)) is not None
        )

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            organization=config.organization,
            project=config.project,
        )
        logger = get_logger(__name__)
        return OpenAIResponsesChatModel(
            client=client,
            model=config.model,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            logger=logger,
            retryable_exceptions=retryable,
        )


def get_provider(name: str) -> LLMProvider:
    """Return a provider instance by name."""
    normalized = name.strip().lower()
    if normalized == "openai":
        return OpenAIProvider()
    if normalized in {"stub", "none"}:
        return StubProvider()
    if normalized == "mock":
        return MockProvider()
    raise ValueError(f"Unsupported LLM provider: {name}")
