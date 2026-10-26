"""Single construction point for provider adapters.

:func:`build_provider` is the only place an adapter is instantiated. Rebuilding
after a provider, model, or key change yields a fresh adapter with a fresh
metadata cache. Building the OpenRouter adapter without a key is prevented
upstream by the Settings validator; a defensive check here fails closed with a
clear error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.providers.base import ProviderError
from hirely.providers.ollama import OllamaAdapter
from hirely.providers.openrouter import OpenRouterAdapter

if TYPE_CHECKING:
    from hirely.config import Settings
    from hirely.providers.base import AIProvider


def build_provider(settings: Settings) -> AIProvider:
    """Build the provider adapter named by the settings.

    Args:
        settings: Validated runtime configuration.

    Returns:
        A freshly constructed adapter implementing :class:`AIProvider`.

    Raises:
        ProviderError: If OpenRouter is selected without an API key. This is
            normally caught earlier by the Settings validator; the check here
            guarantees the factory never builds an unusable OpenRouter adapter.
    """
    if settings.ai_provider == "openrouter":
        if not settings.openrouter_api_key.strip():
            raise ProviderError("OpenRouter selected but OPENROUTER_API_KEY is empty")
        return OpenRouterAdapter(
            settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout_s=settings.request_timeout_s,
            max_retries=settings.max_retries,
        )

    return OllamaAdapter(
        settings.ollama_base_url,
        timeout_s=settings.request_timeout_s,
        max_retries=settings.max_retries,
    )
