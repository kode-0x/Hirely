"""Local Ollama provider adapter.

Ollama runs models locally, so every call is zero API cost. Discovery and
health hit ``GET /api/tags``; inference uses ``POST /api/chat`` with streaming
disabled. All HTTP goes through a shared :class:`httpx.Client` with the
centralized request timeout and the bounded transient-only retry helper.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from hirely.providers.base import ProviderError, ProviderUnavailable
from hirely.providers.retry import retry_transient
from hirely.schemas.provider import ChatResult, ModelInfo, ProviderHealth

if TYPE_CHECKING:
    from pydantic import BaseModel

    from hirely.schemas.provider import ChatMessage

_UNREACHABLE_GUIDANCE = (
    "Ollama is not reachable. Install it from https://ollama.com, start the server "
    "with 'ollama serve', then pull a model with 'ollama pull <model>'."
)


class OllamaAdapter:
    """Provider adapter for a local Ollama server.

    Attributes:
        name: The provider identifier, ``"ollama"``.
    """

    name = "ollama"

    def __init__(
        self, base_url: str = "http://localhost:11434", *, timeout_s: float = 60.0, max_retries: int = 2
    ) -> None:
        """Initialize the adapter.

        Args:
            base_url: Base URL of the local Ollama server.
            timeout_s: Centralized request timeout in seconds.
            max_retries: Bounded transient-only retry count.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._client = httpx.Client(base_url=self._base_url, timeout=timeout_s)

    def list_models(self) -> list[ModelInfo]:
        """Return the locally installed models (never billable).

        An empty list is a valid result: it drives the UI guidance to run
        ``ollama pull <model>``.

        Returns:
            One :class:`ModelInfo` per installed model, each marked free.

        Raises:
            ProviderUnavailable: If the Ollama server cannot be reached.
        """
        data = self._get_tags()
        raw_models = data.get("models", [])
        models = raw_models if isinstance(raw_models, list) else []
        result: list[ModelInfo] = []
        for entry in models:
            model_id = entry.get("name") if isinstance(entry, dict) else None
            if isinstance(model_id, str) and model_id:
                result.append(ModelInfo(id=model_id, source="ollama", free=True))
        return result

    def health(self) -> ProviderHealth:
        """Report whether the local Ollama server is reachable (never billable).

        Returns:
            Healthy status when reachable; otherwise an unhealthy status with
            install and start guidance.
        """
        try:
            self._get_tags()
        except ProviderError:
            return ProviderHealth(ok=False, provider=self.name, detail=_UNREACHABLE_GUIDANCE)
        return ProviderHealth(ok=True, provider=self.name, detail=None)

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        response_model: type[BaseModel] | None = None,
        timeout_s: float | None = None,
    ) -> ChatResult:
        """Run a local chat completion via ``POST /api/chat`` (zero cost).

        Args:
            messages: The ordered conversation.
            model: The locally installed model to call.
            response_model: Optional JSON-only schema request. Ollama returns
                plain text; the raw content is returned for the caller to
                validate.
            timeout_s: Optional per-call timeout override.

        Returns:
            The chat result carrying the raw text and the model identifier.

        Raises:
            ProviderUnavailable: If the server is unreachable or errors.
            ProviderTimeout: If the request exceeds the timeout.
        """
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        timeout = timeout_s if timeout_s is not None else self._timeout_s

        def _call() -> httpx.Response:
            response = self._client.post("/api/chat", json=payload, timeout=timeout)
            response.raise_for_status()
            return response

        response = retry_transient(_call, max_retries=self._max_retries)
        body = response.json()
        content = ""
        if isinstance(body, dict):
            message = body.get("message")
            if isinstance(message, dict):
                content = message.get("content", "") or ""
        return ChatResult(raw_text=content, model=model)

    def _get_tags(self) -> dict[str, object]:
        """Fetch ``/api/tags`` with bounded retries.

        Returns:
            The decoded JSON body as a mapping.

        Raises:
            ProviderUnavailable: If the server is unreachable or errors.
            ProviderTimeout: If the request exceeds the timeout.
        """

        def _call() -> httpx.Response:
            response = self._client.get("/api/tags")
            response.raise_for_status()
            return response

        try:
            response = retry_transient(_call, max_retries=self._max_retries)
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailable("ollama returned an unexpected status") from exc
        body = response.json()
        return body if isinstance(body, dict) else {}
