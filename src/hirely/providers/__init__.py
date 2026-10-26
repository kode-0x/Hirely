"""Provider layer public surface.

Exposes the common :class:`AIProvider` protocol, the typed error hierarchy, the
concrete Ollama and OpenRouter adapters, the free-verification helper, the
bounded retry wrapper, and the single construction entry point.
"""

from __future__ import annotations

from hirely.providers.base import (
    AIProvider,
    FreeVerificationError,
    ModelUnavailable,
    ProviderError,
    ProviderTimeout,
    ProviderUnavailable,
    ResponseValidationError,
)
from hirely.providers.factory import build_provider
from hirely.providers.ollama import OllamaAdapter
from hirely.providers.openrouter import OpenRouterAdapter, verify_free
from hirely.providers.retry import retry_transient

__all__ = [
    "AIProvider",
    "FreeVerificationError",
    "ModelUnavailable",
    "OllamaAdapter",
    "OpenRouterAdapter",
    "ProviderError",
    "ProviderTimeout",
    "ProviderUnavailable",
    "ResponseValidationError",
    "build_provider",
    "retry_transient",
    "verify_free",
]
