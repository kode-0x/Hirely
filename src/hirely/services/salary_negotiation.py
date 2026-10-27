"""Salary-negotiation service.

Salary research reuses the market-research abstraction, so it degrades
identically when no live market data is available: with search disabled, the
endpoint empty/invalid, or the backend unavailable, :class:`SalaryResearch` is
produced with ``citations == []``, ``evidence_type == "estimate"``, and a
mandatory disclosure string equal to the market banner. Model-estimated salary
figures are never presented as researched rates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.config import Settings
from hirely.market.research import NO_DATA_DISCLOSURE, run_market_research
from hirely.schemas.market import MarketSearchFilters
from hirely.schemas.outputs import SalaryResearch

if TYPE_CHECKING:
    from hirely.market.websearch import WebFetch, WebSearch


def research_salary(
    filters: MarketSearchFilters,
    settings: Settings,
    *,
    search: WebSearch | None = None,
    fetch: WebFetch | None = None,
    talking_points: list[str] | None = None,
) -> SalaryResearch:
    """Research salary data for a role, degrading to estimates with disclosure.

    Delegates to :func:`hirely.market.research.run_market_research` so the
    no-network behavior matches Market Research exactly. When the market result
    is an estimate (no live data), the salary result carries no citations, an
    ``estimate`` evidence type, and the shared disclosure banner, and no salary
    range is fabricated.

    Args:
        filters: The validated search filters (``role`` drives the research).
        settings: Runtime configuration (gates and thresholds).
        search: Optional operator-provided search backend.
        fetch: Optional operator-provided fetch backend.
        talking_points: Optional negotiation talking points to carry through.

    Returns:
        The salary research result.
    """
    market = run_market_research(filters, settings, search=search, fetch=fetch)

    if market.evidence_type == "estimate":
        return SalaryResearch(
            role=filters.role,
            evidence_type="estimate",
            disclosure=NO_DATA_DISCLOSURE,
            citations=[],
            talking_points=list(talking_points or []),
        )

    return SalaryResearch(
        role=filters.role,
        evidence_type="observed",
        disclosure=market.disclosure or "",
        citations=list(market.citations),
        talking_points=list(talking_points or []),
    )
