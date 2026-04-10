"""Null (no-op) LLM provider for tests and offline demos.

:class:`NullProvider` always returns a configurable canned response
without making any network calls.  It is safe to use in unit tests,
CI pipelines, and live-demo mode when no real API key is available.
"""
from __future__ import annotations

import time

from .base import BaseLLMProvider, LLMRequest, LLMResponse

_DEFAULT_RESPONSE = (
    "【NullProvider】这是一个本地空提供者的自动回复，无需 API 密钥。"
    "请配置真实的 LLM Provider 以获取有意义的响应。"
)


class NullProvider(BaseLLMProvider):
    """A provider that returns a fixed canned response immediately.

    Useful for:

    * Unit tests that must not make real HTTP calls.
    * Demo mode / offline development.
    * Verifying the provider interface without an API key.

    Args:
        canned_response: Text to return for every :meth:`generate` call.
            Defaults to a Chinese notice message.
        simulated_latency_ms: If > 0, the provider will sleep for this many
            milliseconds to simulate network latency.  Defaults to ``0``.
    """

    def __init__(
        self,
        canned_response: str = _DEFAULT_RESPONSE,
        simulated_latency_ms: int = 0,
    ) -> None:
        self._canned_response = canned_response
        self._simulated_latency_ms = simulated_latency_ms

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Return the canned response, optionally after a simulated delay.

        Args:
            request: The incoming :class:`~app.providers.base.LLMRequest`
                (its fields are ignored except for logging purposes).

        Returns:
            :class:`~app.providers.base.LLMResponse` with the canned text.
        """
        if self._simulated_latency_ms > 0:
            import asyncio

            await asyncio.sleep(self._simulated_latency_ms / 1000.0)

        start = time.monotonic()
        content = self._canned_response
        elapsed_ms = int((time.monotonic() - start) * 1000) + self._simulated_latency_ms

        return LLMResponse(
            content=content,
            model=request.model or "null",
            input_tokens=len(request.prompt.split()),
            output_tokens=len(content.split()),
            latency_ms=elapsed_ms,
        )
