"""Duplicate and stale detection for raw job postings.

Duplicates are detected by a normalized key over title, company, location, and
the canonical URL (scheme/host/path, query and fragment dropped). Staleness is
derived from each posting's published date relative to ``MARKET_STALE_DAYS``: a
date older than the threshold is ``"stale"``, a recent date is ``"fresh"``, and
a missing date is ``"unknown"``.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse

if TYPE_CHECKING:
    from hirely.market.websearch import RawPosting

Freshness = Literal["fresh", "stale", "unknown"]

_WHITESPACE = re.compile(r"\s+")


def _normalize_text(value: str | None) -> str:
    """Normalize a text field for duplicate comparison.

    Lower-cases, strips, and collapses internal whitespace runs.

    Args:
        value: The field value, possibly ``None``.

    Returns:
        The normalized string; empty when the input is ``None`` or blank.
    """
    if not value:
        return ""
    return _WHITESPACE.sub(" ", value.strip().lower())


def _canonical_url(url: str) -> str:
    """Reduce a URL to a canonical form for duplicate comparison.

    Keeps scheme, host, and path (without a trailing slash) and drops query and
    fragment, so tracking parameters do not defeat duplicate detection.

    Args:
        url: The posting URL.

    Returns:
        The canonical URL string.
    """
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    scheme = parsed.scheme.lower()
    return f"{scheme}://{host}{path}" if host else url.strip().lower()


def _dedup_key(posting: RawPosting) -> tuple[str, str, str, str]:
    """Build the normalized duplicate key for a posting.

    Args:
        posting: The raw posting.

    Returns:
        A tuple of normalized title, company, location, and canonical URL.
    """
    return (
        _normalize_text(posting.title),
        _normalize_text(posting.company),
        _normalize_text(posting.location),
        _canonical_url(posting.url),
    )


def deduplicate(postings: list[RawPosting]) -> list[RawPosting]:
    """Remove duplicate postings, preserving first-seen order.

    Two postings are duplicates when their normalized title, company, location,
    and canonical URL all match.

    Args:
        postings: The raw postings, possibly containing duplicates.

    Returns:
        The postings with later duplicates removed.
    """
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[RawPosting] = []
    for posting in postings:
        key = _dedup_key(posting)
        if key in seen:
            continue
        seen.add(key)
        unique.append(posting)
    return unique


def classify_freshness(posted_date: date | None, stale_days: int, *, today: date | None = None) -> Freshness:
    """Classify a posting's freshness against the stale-day threshold.

    Args:
        posted_date: The posting's published date, or ``None`` when unknown.
        stale_days: The age in days beyond which a posting is stale.
        today: Reference date for the comparison; defaults to the current date.

    Returns:
        ``"unknown"`` when no date is present, ``"stale"`` when older than the
        threshold, otherwise ``"fresh"``.
    """
    if posted_date is None:
        return "unknown"
    reference = today if today is not None else date.today()
    if posted_date < reference - timedelta(days=stale_days):
        return "stale"
    return "fresh"
