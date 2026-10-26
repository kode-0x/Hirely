"""OpenRouter provider adapter with fail-closed free-model verification.

Discovery and health are metadata-only (``GET /models``) and never billable.
Before any inference request, :meth:`OpenRouterAdapter.chat` verifies the
target model is free using the model's pricing metadata. Verification fails
closed: if free status is missing, unparseable, or non-zero in any pricing
dimension, the call is refused with no outbound ``/chat/completions`` request.
Nothing auto-reroutes or upgrades to a paid model.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import httpx

from hirely.providers.base import (
    FreeVerificationError,
    ModelUnavailable,
    ProviderError,
    ProviderUnavailable,
    ResponseValidationError,
)
from hirely.providers.retry import retry_transient
from hirely.schemas.provider import ChatResult, ModelInfo, ProviderHealth

if TYPE_CHECKING:
    from pydantic import BaseModel

    from hirely.schemas.provider import ChatMessage


def verify_free(model_id: str, models_metadata: dict[str, dict[str, object]]) -> None:
    """Verify a model is free to call, failing closed on any uncertainty.

    Every value in the model's ``pricing`` mapping must coerce via
    ``Decimal(str(value))`` to exactly ``Decimal("0")``. There is no allow-list
    of pricing keys: all keys are iterated so new paid dimensions cannot slip
    through. A model id merely containing ``"free"`` is never treated as proof.

    Args:
        model_id: The model identifier to verify.
        models_metadata: Mapping of model id to that model's metadata, as cached
            from ``GET /models``.

    Raises:
        FreeVerificationError: If the model is absent, has no usable pricing
            mapping, carries an unparseable pricing value, or has any non-zero
            pricing component.
    """
    entry = models_metadata.get(model_id)
    if entry is None:
        raise FreeVerificationError("model not found in /models metadata")

    pricing = entry.get("pricing")
    if not isinstance(pricing, dict) or not pricing:
        raise FreeVerificationError("no pricing metadata; cannot verify free")

    for value in pricing.values():
        try:
            if Decimal(str(value)) != Decimal("0"):
                raise FreeVerificationError("non-zero pricing component")
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise FreeVerificationError("unparseable pricing; failing closed") from exc


class OpenRouterAdapter:
    """Provider adapter for OpenRouter restricted to free-verified models.

    Attributes:
        name: The provider identifier, ``"openrouter"``.
    """

    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        http_referer: str = "https://github.com/hirely",
        timeout_s: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        """Initialize the adapter.

        Args:
            api_key: OpenRouter API key.
            base_url: OpenRouter API base URL.
            http_referer: Referer header sent with requests.
            timeout_s: Centralized request timeout in seconds.
            max_retries: Bounded transient-only retry count.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout_s,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": http_referer,
                "X-Title": "Hirely",
            },
        )
        self._models_cache: dict[str, dict[str, object]] | None = None

    def list_models(self) -> list[ModelInfo]:
        """Return model discovery metadata (metadata-only, never billable).

        A model is marked free only when :func:`verify_free` succeeds against
        its pricing metadata.

        Returns:
            One :class:`ModelInfo` per advertised model.

        Raises:
            ProviderUnavailable: If the metadata endpoint cannot be reached.
        """
        metadata = self._get_models_metadata()
        result: list[ModelInfo] = []
        for model_id in metadata:
            free = True
            try:
                verify_free(model_id, metadata)
            except FreeVerificationError:
                free = False
            result.append(ModelInfo(id=model_id, source="openrouter", free=free))
        return result

    def health(self) -> ProviderHealth:
        """Report reachability via the metadata endpoint (never billable).

        Returns:
            Healthy status when ``/models`` responds; otherwise an unhealthy
            status with guidance.
        """
        try:
            self._get_models_metadata(force=True)
        except ProviderError:
            return ProviderHealth(
                ok=False,
                provider=self.name,
                detail="OpenRouter is not reachable. Check OPENROUTER_API_KEY and network access.",
            )
        return ProviderHealth(ok=True, provider=self.name, detail=None)

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        response_model: type[BaseModel] | None = None,
        timeout_s: float | None = None,
    ) -> ChatResult:
        """Run a chat completion only after verifying the model is free.

        The target model is verified against cached ``/models`` metadata first.
        Only on success is ``POST /chat/completions`` issued. On verification
        failure no outbound inference request is made.

        Args:
            messages: The ordered conversation.
            model: The model to call; must pass free verification.
            response_model: Optional Pydantic model requesting JSON-only output;
                the response is validated against it.
            timeout_s: Optional per-call timeout override.

        Returns:
            The chat result carrying the raw text and the model identifier.

        Raises:
            FreeVerificationError: If the model is not verified free; no request
                is sent.
            ModelUnavailable: If the model is rate-limited (429) or missing.
            ProviderUnavailable: On outage or authentication failure.
            ResponseValidationError: If a requested structured response fails to
                parse or validate.
            ProviderTimeout: If the request exceeds the timeout.
        """
        metadata = self._get_models_metadata()
        verify_free(model, metadata)

        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        if response_model is not None:
            api_messages.insert(
                0,
                {
                    "role": "system",
                    "content": "Respond with a single valid JSON object only. No prose, no code fences.",
                },
            )

        payload = {"model": model, "messages": api_messages, "stream": False}
        timeout = timeout_s if timeout_s is not None else self._timeout_s

        def _call() -> httpx.Response:
            response = self._client.post("/chat/completions", json=payload, timeout=timeout)
            response.raise_for_status()
            return response

        try:
            response = retry_transient(_call, max_retries=self._max_retries)
        except httpx.HTTPStatusError as exc:
            self._raise_for_status(exc)

        content = self._extract_content(response.json())

        if response_model is not None:
            return self._validate_structured(content, model, response_model)
        return ChatResult(raw_text=content, model=model)

    def _validate_structured(self, content: str, model: str, response_model: type[BaseModel]) -> ChatResult:
        """Validate structured JSON output, raising a handled error on failure.

        Args:
            content: The raw model output expected to contain a JSON object.
            model: The model identifier, for the result.
            response_model: The Pydantic model to validate against.

        Returns:
            A chat result carrying the raw JSON text.

        Raises:
            ResponseValidationError: If no JSON object is found or validation
                fails.
        """
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ResponseValidationError("no JSON object found in model response")
        candidate = content[start : end + 1]
        try:
            response_model.model_validate_json(candidate)
        except ValueError as exc:
            raise ResponseValidationError("structured response failed schema validation") from exc
        return ChatResult(raw_text=candidate, model=model)

    def _raise_for_status(self, exc: httpx.HTTPStatusError) -> None:
        """Map an HTTP error status to a typed provider error (no reroute).

        Args:
            exc: The raised status error.

        Raises:
            ModelUnavailable: For 429 (rate limit) and 404 (missing model).
            ProviderUnavailable: For authentication failures and other statuses.
        """
        status = exc.response.status_code
        if status == 429:
            raise ModelUnavailable("free model is rate-limited; switch to Ollama to continue") from exc
        if status == 404:
            raise ModelUnavailable("model not found on OpenRouter") from exc
        if status in (401, 403):
            raise ProviderUnavailable("OpenRouter authentication failed; check OPENROUTER_API_KEY") from exc
        raise ProviderUnavailable(f"OpenRouter returned status {status}") from exc

    @staticmethod
    def _extract_content(body: object) -> str:
        """Extract the assistant message content from a completion body.

        Args:
            body: The decoded JSON response body.

        Returns:
            The first choice's message content, or an empty string.
        """
        if not isinstance(body, dict):
            return ""
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        return content if isinstance(content, str) else ""

    def _get_models_metadata(self, *, force: bool = False) -> dict[str, dict[str, object]]:
        """Return the cached ``/models`` metadata, fetching it if needed.

        The cache lives for the adapter's lifetime and is always consulted. It
        is rebuilt when the factory rebuilds the adapter. Because verification
        is fail-closed, a stale cache can only over-reject a now-free model,
        never admit a paid one.

        Args:
            force: When ``True``, bypass the cache and refetch (used by health).

        Returns:
            Mapping of model id to that model's metadata dict.

        Raises:
            ProviderUnavailable: If the metadata endpoint cannot be reached.
        """
        if self._models_cache is not None and not force:
            return self._models_cache

        def _call() -> httpx.Response:
            response = self._client.get("/models")
            response.raise_for_status()
            return response

        try:
            response = retry_transient(_call, max_retries=self._max_retries)
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailable("OpenRouter /models request failed") from exc

        metadata: dict[str, dict[str, object]] = {}
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    model_id = entry.get("id")
                    if isinstance(model_id, str):
                        metadata[model_id] = entry

        self._models_cache = metadata
        return metadata
