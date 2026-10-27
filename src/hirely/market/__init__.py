"""Market-research layer: orchestration, backend contract, dedup/stale detection.

Live external job search is disabled by default: the module ships only
:class:`NullBackend` and the :class:`WebSearch`/:class:`WebFetch` adapter
contract. The orchestrator discloses the no-network limitation and never emits
training knowledge as observed findings.
"""

from __future__ import annotations

from hirely.market.dedup import classify_freshness, deduplicate
from hirely.market.research import NO_DATA_DISCLOSURE, run_market_research
from hirely.market.websearch import (
    FetchedPage,
    NullBackend,
    RawPosting,
    WebFetch,
    WebSearch,
)

__all__ = [
    "NO_DATA_DISCLOSURE",
    "FetchedPage",
    "NullBackend",
    "RawPosting",
    "WebFetch",
    "WebSearch",
    "classify_freshness",
    "deduplicate",
    "run_market_research",
]
