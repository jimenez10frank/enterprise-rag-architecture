"""Shared OpenAI chat model wiring for agent nodes.

Centralizes API key checks so importing graph code without a key fails only
when a node that needs the LLM actually runs.
"""

from __future__ import annotations

from typing import TypeVar

from langchain_core.language_models import LanguageModelInput
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.config import settings

T = TypeVar("T", bound=BaseModel)


def chat_openai(*, temperature: float = 0.0) -> ChatOpenAI:
    """Configured ChatOpenAI instance for gpt-4o-mini (STACK.md)."""
    if not settings.openai_api_key:
        msg = "OPENAI_API_KEY is required for agent LLM calls"
        raise ValueError(msg)
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )


def structured_llm(
    model_cls: type[T],
    *,
    temperature: float = 0.0,
) -> Runnable[LanguageModelInput, T]:
    """ChatOpenAI with JSON structured output bound to a Pydantic model."""
    return chat_openai(temperature=temperature).with_structured_output(model_cls)
