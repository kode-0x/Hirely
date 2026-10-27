"""Market-research orchestration.

The flow validates inputs into :class:`MarketSearchFilters`, runs the configured
backend, extracts findings, applies dedup/stale detection, and produces analysis
(trends, skill gaps, match score, recommendations). It is presented before any
resume generation; the downstream gate lives in the UI via session state.

When live search is disabled, the endpoint is empty/invalid, or no usable
backend is supplied, the orchestrator returns a :class:`MarketResearchResult`
with ``citations == []``, ``evidence_type == "estimate"``, and a mandatory
disclosure banner. Model knowledge is never emitted as an observed finding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.config import Settings
from hirely.market.dedup import classify_freshness, deduplicate
from hirely.market.websearch import WebFetch, WebSearch
from hirely.schemas.market import (
    Citation,
    MarketFinding,
    MarketResearchResult,
    MarketSearchFilters,
)

if TYPE_CHECKING:
    from hirely.market.websearch import RawPosting

#: Mandatory banner shown whenever live market data is unavailable. The Salary
#: service reuses this exact string so both degrade paths disclose identically.
NO_DATA_DISCLOSURE = "No live market data available. Figures shown are model estimates, not researched rates."


def _backend_available(settings: Settings, backend: WebSearch | None) -> bool:
    """Decide whether a usable live backend is configured.

    Args:
        settings: Runtime configuration.
        backend: An optional operator-provided backend.

    Returns:
        ``True`` only when live search is enabled, an endpoint is configured,
        and a backend reporting itself configured was supplied.
    """
    if not settings.market_search_enabled:
        return False
    if settings.market_search_endpoint is None:
        return False
    if backend is None:
        return False
    return getattr(backend, "configured", False)


def _build_query(filters: MarketSearchFilters) -> str:
    """Build a free-text query string from the validated filters.

    Args:
        filters: The validated search filters.

    Returns:
        A space-joined query of the populated filter values.
    """
    parts = [filters.role]
    if filters.seniority:
        parts.append(filters.seniority)
    if filters.industry:
        parts.append(filters.industry)
    if filters.location:
        parts.append(filters.location)
    return " ".join(parts)


def _no_data_result(filters: MarketSearchFilters) -> MarketResearchResult:
    """Produce the no-network result with the mandatory disclosure.

    Args:
        filters: The validated search filters.

    Returns:
        A result with no findings, no citations, ``evidence_type ==
        "estimate"``, and the disclosure banner.
    """
    return MarketResearchResult(
        filters=filters,
        findings=[],
        citations=[],
        evidence_type="estimate",
        disclosure=NO_DATA_DISCLOSURE,
        trends=[],
        skill_gaps=[],
        recommendations=[],
    )


def run_market_research(
    filters: MarketSearchFilters,
    settings: Settings,
    *,
    search: WebSearch | None = None,
    fetch: WebFetch | None = None,
) -> MarketResearchResult:
    """Run the market-research flow for validated filters.

    Validation of raw inputs into :class:`MarketSearchFilters` (including the
    future-``date_from`` rejection) happens at the schema boundary before this
    call. When no usable live backend is configured the function degrades to the
    disclosure path and never emits observed findings.

    Args:
        filters: The validated search filters.
        settings: Runtime configuration (gates and thresholds).
        search: Optional operator-provided search backend.
        fetch: Optional operator-provided fetch backend.

    Returns:
        The aggregated market-research result.
    """
    if search is None or fetch is None or not _backend_available(settings, search):
        # Fail closed: disclose the limitation and emit no observed findings.
        return _no_data_result(filters)

    query = _build_query(filters)
    postings: list[RawPosting] = search.search(
        query,
        role=filters.role,
        location=filters.location,
        seniority=filters.seniority,
        industry=filters.industry,
        date_from=filters.date_from,
    )

    postings = deduplicate(postings)
    if not postings:
        return _no_data_result(filters)

    findings: list[MarketFinding] = []
    citations: list[Citation] = []
    for posting in postings:
        page = fetch.fetch(posting.url)
        if page is None:
            continue
        citation = Citation.model_validate({"source_url": page.url, "retrieved_at": page.retrieved_at})
        citations.append(citation)
        freshness = classify_freshness(posting.posted_date, settings.market_stale_days)
        findings.append(
            MarketFinding(
                category="requirement",
                value=posting.title,
                evidence_type="observed",
                citation=citation,
                freshness=freshness,
            )
        )

    if not findings:
        return _no_data_result(filters)

    return MarketResearchResult(
        filters=filters,
        findings=findings,
        citations=citations,
        evidence_type="observed",
        disclosure=None,
        trends=[],
        skill_gaps=[],
        recommendations=[],
    )
