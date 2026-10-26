"""Common provider interface and typed error hierarchy.

Every AI backend (Ollama, OpenRouter) implements the :class:`AIProvider`
protocol so services depend only on this contract, never on a concrete HTTP
client. Discovery and health are never billable; only :meth:`AIProvider.chat`
may issue an inference request, and only after any provider-specific free
verification has passed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pydantic import BaseModel

    from hirely.schemas.provider import ChatMessage, ChatResult, ModelInfo, ProviderHealth


class ProviderError(Exception):
    """Base class for all provider-layer errors.

    Services catch this type and map it to a UI-safe message; raw exceptions
    and stack traces never reach the presentation layer.
    """


class ProviderUnavailable(ProviderError):
    """The provider is unreachable or returned a server-side outage."""


class ModelUnavailable(ProviderError):
    """The requested model is missing or rate-limited (HTTP 429)."""


class FreeVerificationError(ProviderError):
    """A model's free status could not be verified, so the call is refused.

    Raised by the OpenRouter adapter when pricing metadata is missing,
    unparseable, or non-zero. Verification fails closed: no inference request
    is issued when free status is uncertain.
    """


class ResponseValidationError(ProviderError):
    """A structured response could not be parsed into its schema."""


class ProviderTimeout(ProviderError):
    """A request exceeded the centralized request timeout."""


@runtime_checkable
class AIProvider(Protocol):
    """Typed contract implemented by every provider adapter.

    Attributes:
        name: Stable provider identifier (for example ``"ollama"``).
    """

    name: str

    def list_models(self) -> list[ModelInfo]:
        """Return discovery metadata for available models.

        This call is never billable: it reports which models exist and, where
        known, whether they are free to call.

        Returns:
            The available models as :class:`ModelInfo` entries.
        """
        ...

    def health(self) -> ProviderHealth:
        """Report provider connectivity.

        This call is never billable and never issues an inference request.

        Returns:
            The provider's reachability and any actionable guidance.
        """
        ...

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        response_model: type[BaseModel] | None = None,
        timeout_s: float | None = None,
    ) -> ChatResult:
        """Run a chat completion.

        Args:
            messages: The ordered conversation. Untrusted user content must use
                the ``"user"`` role; framework guidance belongs in ``"system"``.
            model: The model identifier to call.
            response_model: Optional Pydantic model requesting JSON-only output;
                the raw text is validated against it.
            timeout_s: Optional per-call timeout override in seconds.

        Returns:
            The chat result carrying the raw text and the model identifier.

        Raises:
            ProviderError: On any provider failure (unavailable, model
                unavailable, free-verification failure, response validation
                failure, or timeout).
        """
        ...
