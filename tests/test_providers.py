"""Unit tests for the LLM providers."""
from __future__ import annotations

import asyncio

import pytest

from app.providers import BaseLLMProvider, LLMRequest, LLMResponse, NullProvider


# ---------------------------------------------------------------------------
# LLMRequest
# ---------------------------------------------------------------------------


def test_llm_request_defaults() -> None:
    req = LLMRequest(prompt="hello")
    assert req.prompt == "hello"
    assert req.system == ""
    assert req.model == ""
    assert req.temperature is None
    assert req.max_tokens is None
    assert req.metadata == {}


def test_llm_request_is_frozen() -> None:
    req = LLMRequest(prompt="hi")
    with pytest.raises((AttributeError, TypeError)):
        req.prompt = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------


def test_llm_response_basic() -> None:
    resp = LLMResponse(content="result", model="gpt-4o", latency_ms=42)
    assert resp.content == "result"
    assert resp.model == "gpt-4o"
    assert resp.latency_ms == 42


# ---------------------------------------------------------------------------
# NullProvider
# ---------------------------------------------------------------------------


def test_null_provider_default_canned_response() -> None:
    provider = NullProvider()
    req = LLMRequest(prompt="test")
    resp = asyncio.run(provider.generate(req))
    assert "NullProvider" in resp.content


def test_null_provider_custom_canned_response() -> None:
    provider = NullProvider(canned_response="custom reply")
    req = LLMRequest(prompt="test")
    resp = asyncio.run(provider.generate(req))
    assert resp.content == "custom reply"


def test_null_provider_model_from_request() -> None:
    provider = NullProvider()
    req = LLMRequest(prompt="hi", model="my-model")
    resp = asyncio.run(provider.generate(req))
    assert resp.model == "my-model"


def test_null_provider_model_fallback_to_null() -> None:
    provider = NullProvider()
    req = LLMRequest(prompt="hi")
    resp = asyncio.run(provider.generate(req))
    assert resp.model == "null"


def test_null_provider_returns_token_counts() -> None:
    provider = NullProvider(canned_response="one two three four")
    req = LLMRequest(prompt="word1 word2")
    resp = asyncio.run(provider.generate(req))
    assert resp.input_tokens == 2
    assert resp.output_tokens == 4


def test_null_provider_generate_sync() -> None:
    provider = NullProvider(canned_response="sync reply")
    req = LLMRequest(prompt="test")
    resp = provider.generate_sync(req)
    assert resp.content == "sync reply"


def test_null_provider_is_base_llm_provider() -> None:
    provider = NullProvider()
    assert isinstance(provider, BaseLLMProvider)


# ---------------------------------------------------------------------------
# BaseLLMProvider cannot be instantiated directly
# ---------------------------------------------------------------------------


def test_base_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseLLMProvider()  # type: ignore[abstract]
