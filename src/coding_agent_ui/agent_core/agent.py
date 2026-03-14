"""Agent wrapper around LangChain models and structured prompts."""

from __future__ import annotations

import json
from typing import Any, Dict, Type

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from coding_agent_ui.agent_core.policy import AgentPolicy
from coding_agent_ui.tools.registry import ToolRegistry


class StructuredOutputError(RuntimeError):
    """Raised when structured output parsing fails."""

    def __init__(self, message: str, raw_output: str, errors: str) -> None:
        super().__init__(message)
        self.raw_output = raw_output
        self.errors = errors


class Agent:
    """LLM-backed agent with policy and tool registry."""

    def __init__(self, llm: BaseChatModel, policy: AgentPolicy, tools: ToolRegistry) -> None:
        self._llm = llm
        self._policy = policy
        self._tools = tools

    @property
    def tools(self) -> ToolRegistry:
        """Expose the tool registry."""
        return self._tools

    @property
    def policy(self) -> AgentPolicy:
        """Expose the active policy."""
        return self._policy

    def invoke_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Type[BaseModel],
        variables: Dict[str, Any],
    ) -> BaseModel:
        """Run a structured LLM call using the provided schema.

        Retries once if the model returns malformed output.
        """
        parser = PydanticOutputParser(pydantic_object=schema)

        def build_prompt(extra_system: str | None = None) -> ChatPromptTemplate:
            messages = [("system", system_prompt), ("human", user_prompt)]
            if extra_system:
                messages.append(("system", extra_system))
            return ChatPromptTemplate.from_messages(messages).partial(
                format_instructions=parser.get_format_instructions()
            )

        attempts = [
            build_prompt(),
            build_prompt(
                "IMPORTANT: Return only valid JSON that matches the schema. "
                "Do not include markdown, comments, or trailing text."
            ),
        ]

        last_error = ""
        raw_output = ""

        for prompt in attempts:
            messages = prompt.format_messages(**variables)
            response = self._llm.invoke(messages)
            raw_output = self._extract_content(response)
            try:
                return parser.parse(raw_output)
            except Exception as exc:
                last_error = str(exc)

        truncated = raw_output[:4000]
        raise StructuredOutputError(
            "Failed to parse structured output after retry.",
            raw_output=truncated,
            errors=last_error,
        )

    def _extract_content(self, response: Any) -> str:
        """Extract a string payload from an LLM response."""
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return json.dumps(content, ensure_ascii=False)
        if isinstance(content, list):
            parts = []
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
