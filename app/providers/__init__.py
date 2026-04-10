"""LLM Provider abstraction package.

Providers expose a common interface so that the application layer can call
language models without depending on any specific vendor SDK.  The
:class:`NullProvider` ships with the package and is used in tests and offline
demos; real providers (OpenAI, Anthropic, local Ollama …) can be added by
implementing :class:`BaseLLMProvider`.
"""
from __future__ import annotations

from .base import BaseLLMProvider, LLMRequest, LLMResponse
from .null_provider import NullProvider

__all__ = [
    "BaseLLMProvider",
    "LLMRequest",
    "LLMResponse",
    "NullProvider",
]
