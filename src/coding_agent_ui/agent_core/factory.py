"""Factories for building agent instances."""

from __future__ import annotations

from coding_agent_ui.agent_core.agent import Agent
from coding_agent_ui.agent_core.llm import LLMConfig, get_provider
from coding_agent_ui.agents.frontend.policy import FrontendPolicy
from coding_agent_ui.config.settings import Settings
from coding_agent_ui.tools.registry import ToolRegistry


def create_llm(settings: Settings):
    """Create an LLM instance from settings."""
    provider = get_provider(settings.llm_provider)
    config = LLMConfig(
        provider=settings.llm_provider,
        model=settings.model_name,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        organization=settings.openai_organization,
        project=settings.openai_project,
    )
    return provider.create(config)


def create_frontend_agent(*, settings: Settings, tools: ToolRegistry):
    """Create the frontend-specialized agent."""
    llm = create_llm(settings)
    policy = FrontendPolicy()
    return Agent(llm=llm, policy=policy, tools=tools)
