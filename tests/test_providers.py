"""Provider-layer tests: Ollama adapter, OpenRouter fail-closed verification,
no-reroute behavior, and structured response validation.

All HTTP is intercepted with respx; no socket is opened and no billable
inference request is issued except where a free-verified call is explicitly
expected.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from hirely.providers.base import (
    FreeVerificationError,
    ModelUnavailable,
    ProviderUnavailable,
    ResponseValidationError,
)
from hirely.providers.ollama import OllamaAdapter
from hirely.providers.openrouter import OpenRouterAdapter, verify_free
from hirely.schemas.provider import ChatMessage
from tests.conftest import build_models_payload, chat_completion_body

OLLAMA_URL = "http://localhost:11434"
OPENROUTER_URL = "https://openrouter.ai/api/v1"


# --- Ollama adapter (9.1) ---------------------------------------------------


@respx.mock
def test_ollama_list_models_parses_tags() -> None:
    respx.get(f"{OLLAMA_URL}/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "llama3"}, {"name": "qwen2"}]})
    )
    adapter = OllamaAdapter(OLLAMA_URL, max_retries=0)
    models = adapter.list_models()
    assert [m.id for m in models] == ["llama3", "qwen2"]
    assert all(m.free for m in models)


@respx.mock
def test_ollama_empty_model_list_is_valid_guidance() -> None:
    respx.get(f"{OLLAMA_URL}/api/tags").mock(return_value=httpx.Response(200, json={"models": []}))
    adapter = OllamaAdapter(OLLAMA_URL, max_retries=0)
    assert adapter.list_models() == []


@respx.mock
def test_ollama_health_unreachable_returns_guidance() -> None:
    respx.get(f"{OLLAMA_URL}/api/tags").mock(side_effect=httpx.ConnectError("refused"))
    adapter = OllamaAdapter(OLLAMA_URL, max_retries=0)
    health = adapter.health()
    assert health.ok is False
    assert "ollama" in (health.detail or "").lower()


@respx.mock
def test_ollama_chat_returns_message_content() -> None:
    respx.post(f"{OLLAMA_URL}/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"role": "assistant", "content": "hello"}})
    )
    adapter = OllamaAdapter(OLLAMA_URL, max_retries=0)
    result = adapter.chat([ChatMessage(role="user", content="hi")], model="llama3")
    assert result.raw_text == "hello"
    assert result.model == "llama3"


# --- OpenRouter fail-closed verify_free (9.2) -------------------------------


def test_verify_free_accepts_all_zero_pricing() -> None:
    meta = {"m": {"pricing": {"prompt": "0", "completion": "0", "request": "0"}}}
    verify_free("m", meta)  # no exception


def test_verify_free_rejects_missing_model() -> None:
    with pytest.raises(FreeVerificationError):
        verify_free("absent", {})


def test_verify_free_rejects_missing_pricing() -> None:
    with pytest.raises(FreeVerificationError):
        verify_free("m", {"m": {}})


def test_verify_free_rejects_unparseable_pricing() -> None:
    with pytest.raises(FreeVerificationError):
        verify_free("m", {"m": {"pricing": {"prompt": "free"}}})


def test_verify_free_rejects_nonzero_pricing() -> None:
    with pytest.raises(FreeVerificationError):
        verify_free("m", {"m": {"pricing": {"prompt": "0", "completion": "0.000002"}}})


def test_verify_free_name_containing_free_is_not_proof() -> None:
    # A "free"-named model with a paid pricing dimension must still be rejected.
    with pytest.raises(FreeVerificationError):
        verify_free("vendor/model-free", {"vendor/model-free": {"pricing": {"prompt": "0.01", "completion": "0"}}})


@respx.mock
def test_openrouter_chat_rejects_paid_model_without_inference_call() -> None:
    models_route = respx.get(f"{OPENROUTER_URL}/models").mock(
        return_value=httpx.Response(200, json=build_models_payload({"paid/model": {"pricing": {"prompt": "0.01"}}}))
    )
    chat_route = respx.post(f"{OPENROUTER_URL}/chat/completions")
    adapter = OpenRouterAdapter("key", base_url=OPENROUTER_URL, max_retries=0)
    with pytest.raises(FreeVerificationError):
        adapter.chat([ChatMessage(role="user", content="hi")], model="paid/model")
    assert models_route.called
    assert not chat_route.called  # fail closed: no /chat/completions request


@respx.mock
def test_openrouter_discovery_only_hits_models() -> None:
    models_route = respx.get(f"{OPENROUTER_URL}/models").mock(
        return_value=httpx.Response(
            200,
            json=build_models_payload(
                {
                    "free/model": {"pricing": {"prompt": "0", "completion": "0"}},
                    "paid/model": {"pricing": {"prompt": "0.5"}},
                }
            ),
        )
    )
    chat_route = respx.post(f"{OPENROUTER_URL}/chat/completions")
    adapter = OpenRouterAdapter("key", base_url=OPENROUTER_URL, max_retries=0)
    models = adapter.list_models()
    free = {m.id: m.free for m in models}
    assert free == {"free/model": True, "paid/model": False}
    assert models_route.called
    assert not chat_route.called


@respx.mock
def test_openrouter_chat_free_model_issues_request() -> None:
    respx.get(f"{OPENROUTER_URL}/models").mock(
        return_value=httpx.Response(
            200, json=build_models_payload({"free/model": {"pricing": {"prompt": "0", "completion": "0"}}})
        )
    )
    chat_route = respx.post(f"{OPENROUTER_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_completion_body("ok"))
    )
    adapter = OpenRouterAdapter("key", base_url=OPENROUTER_URL, max_retries=0)
    result = adapter.chat([ChatMessage(role="user", content="hi")], model="free/model")
    assert result.raw_text == "ok"
    assert chat_route.called


# --- No reroute on 429 / outage (9.3) ---------------------------------------


@respx.mock
def test_openrouter_429_raises_model_unavailable_no_reroute() -> None:
    respx.get(f"{OPENROUTER_URL}/models").mock(
        return_value=httpx.Response(
            200, json=build_models_payload({"free/model": {"pricing": {"prompt": "0", "completion": "0"}}})
        )
    )
    chat_route = respx.post(f"{OPENROUTER_URL}/chat/completions").mock(return_value=httpx.Response(429))
    adapter = OpenRouterAdapter("key", base_url=OPENROUTER_URL, max_retries=0)
    with pytest.raises(ModelUnavailable):
        adapter.chat([ChatMessage(role="user", content="hi")], model="free/model")
    # One attempt only: 429 is not retried and never reroutes to another model.
    assert chat_route.call_count == 1


@respx.mock
def test_openrouter_auth_failure_raises_unavailable() -> None:
    respx.get(f"{OPENROUTER_URL}/models").mock(
        return_value=httpx.Response(
            200, json=build_models_payload({"free/model": {"pricing": {"prompt": "0", "completion": "0"}}})
        )
    )
    respx.post(f"{OPENROUTER_URL}/chat/completions").mock(return_value=httpx.Response(401))
    adapter = OpenRouterAdapter("key", base_url=OPENROUTER_URL, max_retries=0)
    with pytest.raises(ProviderUnavailable):
        adapter.chat([ChatMessage(role="user", content="hi")], model="free/model")


# --- Response validation (9.4) ----------------------------------------------


@respx.mock
def test_openrouter_structured_response_invalid_json_raises() -> None:
    from pydantic import BaseModel

    class Shape(BaseModel):
        value: int

    respx.get(f"{OPENROUTER_URL}/models").mock(
        return_value=httpx.Response(
            200, json=build_models_payload({"free/model": {"pricing": {"prompt": "0", "completion": "0"}}})
        )
    )
    respx.post(f"{OPENROUTER_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_completion_body("not json at all"))
    )
    adapter = OpenRouterAdapter("key", base_url=OPENROUTER_URL, max_retries=0)
    with pytest.raises(ResponseValidationError):
        adapter.chat([ChatMessage(role="user", content="hi")], model="free/model", response_model=Shape)


@respx.mock
def test_openrouter_structured_response_schema_mismatch_raises() -> None:
    from pydantic import BaseModel

    class Shape(BaseModel):
        value: int

    respx.get(f"{OPENROUTER_URL}/models").mock(
        return_value=httpx.Response(
            200, json=build_models_payload({"free/model": {"pricing": {"prompt": "0", "completion": "0"}}})
        )
    )
    respx.post(f"{OPENROUTER_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_completion_body('{"value": "not-an-int"}'))
    )
    adapter = OpenRouterAdapter("key", base_url=OPENROUTER_URL, max_retries=0)
    with pytest.raises(ResponseValidationError):
        adapter.chat([ChatMessage(role="user", content="hi")], model="free/model", response_model=Shape)
