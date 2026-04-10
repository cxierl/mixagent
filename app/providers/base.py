"""Abstract base class and value objects for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Input value object for an LLM call.

    Attributes:
        prompt:      The user-facing prompt text.
        system:      Optional system instruction prepended before the user prompt.
        model:       Model identifier string (provider-specific).
        temperature: Sampling temperature; ``None`` uses the provider default.
        max_tokens:  Maximum tokens to generate; ``None`` uses the provider default.
        metadata:    Arbitrary key-value data passed through for logging/tracing.
    """

    prompt: str
    system: str = ""
    model: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Output value object returned by an LLM provider.

    Attributes:
        content:      The generated text.
        model:        The model identifier that produced the response.
        input_tokens: Number of tokens consumed from the prompt (if reported).
        output_tokens: Number of tokens in the completion (if reported).
        latency_ms:   Wall-clock time in milliseconds for the API call.
    """

    content: str
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None


class BaseLLMProvider(ABC):
    """Abstract interface that all LLM provider adapters must implement.

    Subclasses only need to implement :meth:`generate`.  The ``generate_sync``
    convenience wrapper is provided for callers that cannot use ``async``.
    """

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send *request* to the underlying model and return the response.

        Args:
            request: Fully populated :class:`LLMRequest`.

        Returns:
            :class:`LLMResponse` with the generated text and metadata.

        Raises:
            ProviderError: On unrecoverable API or network errors (subclasses
                may define their own exception hierarchy).
        """

    def generate_sync(self, request: LLMRequest) -> LLMResponse:
        """Synchronous wrapper around :meth:`generate`.

        Runs the coroutine in a new event loop so that synchronous callers
        (e.g. tests, CLI scripts) can invoke the provider without managing
        ``asyncio`` directly.

        Args:
            request: Fully populated :class:`LLMRequest`.

        Returns:
            :class:`LLMResponse` with the generated text and metadata.
        """
        import asyncio

        return asyncio.run(self.generate(request))
