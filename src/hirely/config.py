"""Application configuration loaded from the environment and an optional .env file.

Defaults never point at a paid AI service, and the zero-cost guarantee is
enforced by a model validator: selecting OpenRouter requires an explicit API
key, while the default Ollama provider requires no OpenRouter configuration at
all.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration for Hirely.

    Values are read from process environment variables and, when present, a
    local ``.env`` file. Environment variable names are the upper-case form of
    each field (for example ``AI_PROVIDER`` maps to :attr:`ai_provider`).

    Attributes:
        ai_provider: Active AI provider; defaults to local Ollama.
        ollama_base_url: Base URL of the local Ollama server.
        ollama_model: Selected Ollama model; empty means choose at runtime.
        openrouter_api_key: OpenRouter key; required only for OpenRouter.
        openrouter_model: Selected OpenRouter model; must pass free verification.
        openrouter_base_url: OpenRouter API base URL.
        request_timeout_s: Centralized provider HTTP timeout in seconds.
        max_retries: Bounded transient-only retry count.
        max_upload_mb: Authoritative upload size cap in megabytes.
        market_search_enabled: Gate for live market research.
        market_search_endpoint: Optional keyless market-search endpoint.
        market_stale_days: Age threshold for flagging stale job listings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ai_provider: Literal["ollama", "openrouter"] = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""

    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    request_timeout_s: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    max_upload_mb: int = Field(default=10, gt=0)

    market_search_enabled: bool = False
    market_search_endpoint: HttpUrl | None = None
    market_stale_days: int = Field(default=45, gt=0)

    @field_validator("market_search_endpoint", mode="before")
    @classmethod
    def _blank_endpoint_is_none(cls, value: object) -> object:
        """Treat an empty or whitespace-only endpoint as unset.

        An enabled-but-empty endpoint must fall back to the no-network path
        rather than raising a validation error at startup.

        Args:
            value: The raw environment value for the endpoint.

        Returns:
            ``None`` when the value is blank, otherwise the value unchanged.
        """
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @model_validator(mode="after")
    def _validate_provider_requirements(self) -> Settings:
        """Enforce zero-cost provider rules.

        Selecting OpenRouter requires a non-empty API key so Hirely never
        attempts an unauthenticated paid call. The default Ollama provider is
        fully local and requires no OpenRouter configuration.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If OpenRouter is selected without an API key.
        """
        if self.ai_provider == "openrouter" and not self.openrouter_api_key.strip():
            raise ValueError(
                "AI_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is empty. "
                "Set OPENROUTER_API_KEY, or use AI_PROVIDER=ollama for the default local provider."
            )
        return self
