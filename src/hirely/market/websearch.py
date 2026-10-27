"""Web-search/fetch adapter contract and the default NullBackend.

This module defines the :class:`WebSearch` and :class:`WebFetch` ``typing``
protocols that an operator-implemented market backend must satisfy. Hirely
ships a single concrete implementation, :class:`NullBackend`, which returns no
results and reports that search is not configured. No concrete live backend is
shipped: live external job search is disabled by default, and a real backend is
an operator responsibility that conforms to these protocols without Hirely
performing any outbound web request out of the box.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class RawPosting(BaseModel):
    """A raw job posting returned by a search backend.

    Attributes:
        title: Posting title.
        company: Hiring company name.
        location: Posting location, when provided.
        url: Canonical posting URL.
        posted_date: Date the posting was published, when known.
        snippet: Short description or search snippet, when provided.
    """

    title: str
    company: str
    location: str | None = None
    url: str
    posted_date: date | None = None
    snippet: str | None = None


class FetchedPage(BaseModel):
    """The fetched text content of a posting URL.

    Attributes:
        url: The URL that was fetched.
        text: Extracted page text.
        retrieved_at: Date the page was retrieved.
    """

    url: str
    text: str
    retrieved_at: date


@runtime_checkable
class WebSearch(Protocol):
    """Contract for a job-posting search backend.

    ``search`` receives only the validated, non-blank filters. Implementations
    must respect site terms and rate limits and must never fabricate results.

    Attributes:
        configured: Whether the backend is able to perform live searches.
    """

    configured: bool

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
        """Return candidate postings for the given validated filters.

        Args:
            query: Free-text query string derived from the filters.
            role: The required target role.
            location: Optional location filter.
            seniority: Optional seniority filter.
            industry: Optional industry filter.
            date_from: Optional earliest posting date.

        Returns:
            The candidate postings; an empty list when nothing matches or the
            backend is not configured.
        """
        ...


@runtime_checkable
class WebFetch(Protocol):
    """Contract for fetching the text of a posting URL.

    Implementations must only fetch URLs produced by the paired
    :class:`WebSearch`, never arbitrary user-supplied URLs, and must not cross
    authentication walls or bypass rate limits.
    """

    def fetch(self, url: str) -> FetchedPage | None:
        """Fetch and extract the text content of a posting URL.

        Args:
            url: The posting URL to fetch.

        Returns:
            The fetched page, or ``None`` when the URL cannot be retrieved.
        """
        ...


class NullBackend:
    """The default no-op backend: no results, not configured.

    Returns no postings and fetches nothing. Its presence drives the
    no-network disclosure path in :mod:`hirely.market.research` and the Salary
    service, so Hirely never fabricates market data out of the box.

    Attributes:
        configured: Always ``False``.
    """

    configured = False

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
        """Return no postings (search is not configured).

        Args:
            query: Ignored.
            role: Ignored.
            location: Ignored.
            seniority: Ignored.
            industry: Ignored.
            date_from: Ignored.

        Returns:
            An empty list.
        """
        return []

    def fetch(self, url: str) -> FetchedPage | None:
        """Fetch nothing (search is not configured).

        Args:
            url: Ignored.

        Returns:
            ``None``.
        """
        return None
