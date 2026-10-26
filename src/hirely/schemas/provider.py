"""Schemas for the AI provider layer.

These models form the typed contract between services and provider adapters
(Ollama, OpenRouter). They carry chat messages, model discovery metadata, chat
results, and provider health, independent of any concrete HTTP backend.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat exchange.

    Attributes:
        role: The speaker role. Untrusted user content must always use the
            ``"user"`` role; framework guidance belongs in ``"system"``.
        content: The message text.
    """

    role: Literal["system", "user", "assistant"]
    content: str


class ModelInfo(BaseModel):
    """Discovery metadata for a single model.

    Attributes:
        id: Provider-specific model identifier.
        source: Provider name that offers the model.
        free: Whether the model is verified free to call.
    """

    id: str
    source: str
    free: bool = False


class ChatResult(BaseModel):
    """Result of a chat completion request.

    Attributes:
        raw_text: The raw text returned by the model.
        model: The model identifier that produced the result.
    """

    raw_text: str
    model: str


class ProviderHealth(BaseModel):
    """Connectivity status for a provider.

    Attributes:
        ok: Whether the provider is reachable.
        provider: The provider name.
        detail: Optional human-readable detail or guidance.
    """

    ok: bool
    provider: str
    detail: str | None = Field(default=None)
