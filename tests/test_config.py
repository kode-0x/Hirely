"""Configuration validation tests.

Ollama needs no key; selecting OpenRouter without a key fails clearly. The
market endpoint falls back to None when blank.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hirely.config import Settings


def test_ollama_default_requires_no_key() -> None:
    settings = Settings(ai_provider="ollama", openrouter_api_key="")
    assert settings.ai_provider == "ollama"


def test_openrouter_without_key_fails_clearly() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(ai_provider="openrouter", openrouter_api_key="")
    assert "OPENROUTER_API_KEY" in str(exc.value)


def test_openrouter_with_key_ok() -> None:
    settings = Settings(ai_provider="openrouter", openrouter_api_key="sk-test")
    assert settings.ai_provider == "openrouter"


def test_blank_market_endpoint_coerces_to_none() -> None:
    settings = Settings(ai_provider="ollama", market_search_enabled=True, market_search_endpoint="   ")
    assert settings.market_search_endpoint is None
