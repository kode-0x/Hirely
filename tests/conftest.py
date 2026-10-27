"""Shared pytest fixtures and fakes for the Hirely suite.

Every external dependency is faked or mocked here: no test opens a real network
connection and no test issues a billable AI request. HTTP is intercepted with
respx over httpx; the web-search/fetch backends used by the market layer are
in-memory fakes that capture their keyword arguments so filter pass-through can
be asserted.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from hirely.market.websearch import FetchedPage, RawPosting

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    """Return the raw bytes of a committed test fixture.

    Args:
        name: Filename under ``tests/fixtures``.

    Returns:
        The fixture file contents.
    """
    return (FIXTURES_DIR / name).read_bytes()


class FakeUpload:
    """Minimal stand-in for a Streamlit ``UploadedFile`` (matches UploadLike)."""

    def __init__(self, name: str, data: bytes, type_: str = "") -> None:
        self.name = name
        self.type = type_
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


class RecordingWebSearch:
    """A WebSearch fake that records its kwargs and returns canned postings.

    Attributes:
        configured: Whether the backend reports itself able to search.
        calls: One dict of captured keyword arguments per ``search`` call.
    """

    def __init__(self, postings: list[RawPosting] | None = None, *, configured: bool = True) -> None:
        self.configured = configured
        self._postings = postings or []
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        *,
        role: str,
        location: str | None,
        seniority: str | None,
        industry: str | None,
        date_from: date | None,
    ) -> list[RawPosting]:
        self.calls.append(
            {
                "query": query,
                "role": role,
                "location": location,
                "seniority": seniority,
                "industry": industry,
                "date_from": date_from,
            }
        )
        return list(self._postings)


class RecordingWebFetch:
    """A WebFetch fake that records fetched URLs and returns canned pages.

    Attributes:
        calls: The URLs passed to ``fetch`` in order.
    """

    def __init__(self, pages: dict[str, FetchedPage] | None = None) -> None:
        self._pages = pages or {}
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchedPage | None:
        self.calls.append(url)
        return self._pages.get(url)


@pytest.fixture
def recording_search() -> RecordingWebSearch:
    """Return a configured recording search backend with no postings."""
    return RecordingWebSearch(configured=True)


@pytest.fixture
def fake_upload() -> type[FakeUpload]:
    """Return the FakeUpload class for building uploads in tests."""
    return FakeUpload


class RecordingProvider:
    """An AIProvider fake that records chat calls and returns canned text.

    It never performs HTTP; it exists so service-layer tests can assert whether
    a provider call was made without touching a network.

    Attributes:
        name: Provider identifier.
        chat_calls: Captured chat invocations.
    """

    name = "fake"

    def __init__(self, raw_text: str = "{}") -> None:
        self._raw_text = raw_text
        self.chat_calls: list[dict[str, Any]] = []

    def list_models(self) -> list[Any]:
        return []

    def health(self) -> Any:  # pragma: no cover - not exercised
        raise NotImplementedError

    def chat(
        self, messages: list[Any], *, model: str, response_model: Any = None, timeout_s: float | None = None
    ) -> Any:
        from hirely.schemas.provider import ChatResult

        self.chat_calls.append({"messages": messages, "model": model, "response_model": response_model})
        return ChatResult(raw_text=self._raw_text, model=model)


@pytest.fixture
def recording_provider() -> type[RecordingProvider]:
    """Return the RecordingProvider class for service tests."""
    return RecordingProvider


@pytest.fixture
def mock_transport() -> None:
    """Placeholder guard documenting that all HTTP is mocked via respx.

    Tests that need HTTP use the ``respx_mock`` fixture (via the ``@respx.mock``
    decorator or ``respx.mock`` context manager) so httpx never opens a socket.
    """
    return None


def build_models_payload(models: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build an OpenRouter ``/models`` response body from id -> entry mapping.

    Args:
        models: Mapping of model id to its metadata entry (including pricing).

    Returns:
        A body shaped like OpenRouter's ``/models`` response.
    """
    return {"data": [{"id": model_id, **entry} for model_id, entry in models.items()]}


def chat_completion_body(content: str) -> dict[str, Any]:
    """Build an OpenRouter ``/chat/completions`` response body.

    Args:
        content: The assistant message content to embed.

    Returns:
        A minimal completion body carrying the content.
    """
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def assert_no_real_connection(request: httpx.Request) -> None:  # pragma: no cover - safety net
    """Fail loudly if any unmocked request escapes to the network.

    Args:
        request: The outgoing request intercepted by respx.
    """
    raise AssertionError(f"unmocked network call to {request.url}")
