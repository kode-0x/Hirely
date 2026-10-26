"""Schemas for market research.

These models enforce the evidence discipline of the core workflow: observed
findings cannot exist without a citation, search filters are validated before
reaching any backend, and a ``date_from`` filter can never be in the future.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, model_validator


def _reject_future_date(value: date) -> date:
    """Reject a date that lies in the future.

    Args:
        value: The candidate date.

    Returns:
        The date unchanged when it is today or earlier.

    Raises:
        ValueError: If the date is later than today.
    """
    if value > date.today():
        raise ValueError("date_from cannot be in the future")
    return value


class MarketSearchFilters(BaseModel):
    """Validated filters for a market-research query.

    Attributes:
        role: Target role; required and non-empty after stripping.
        location: Optional location, stripped, max 120 characters.
        industry: Optional industry, stripped, max 120 characters.
        seniority: Optional seniority level from a fixed vocabulary.
        date_from: Optional earliest posting date; must not be in the future.
    """

    role: str = Field(min_length=1)
    location: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    seniority: Literal["intern", "junior", "mid", "senior", "lead", "principal"] | None = None
    date_from: Annotated[date, AfterValidator(_reject_future_date)] | None = None

    model_config = {"str_strip_whitespace": True}


class Citation(BaseModel):
    """A source reference for an observed finding.

    Attributes:
        source_url: URL of the fetched source.
        retrieved_at: Date the source was retrieved.
    """

    source_url: HttpUrl
    retrieved_at: date


class MarketFinding(BaseModel):
    """A single market-research finding.

    Observed findings must carry a citation; estimates need not. This makes
    "observed without a citation" unrepresentable.

    Attributes:
        category: The kind of finding.
        value: The finding text.
        evidence_type: Whether the finding was observed or estimated.
        citation: Source reference; required when observed.
        freshness: Freshness classification of the source.
    """

    category: Literal["skill", "tool", "qualification", "keyword", "salary", "requirement"]
    value: str
    evidence_type: Literal["observed", "estimate"]
    citation: Citation | None = None
    freshness: Literal["fresh", "stale", "unknown"] = "unknown"

    @model_validator(mode="after")
    def observed_needs_citation(self) -> MarketFinding:
        """Require a citation for observed findings.

        Returns:
            The validated finding.

        Raises:
            ValueError: If an observed finding has no citation.
        """
        if self.evidence_type == "observed" and self.citation is None:
            raise ValueError("observed finding must carry a citation")
        return self


class MarketResearchResult(BaseModel):
    """Aggregated result of a market-research run.

    Attributes:
        filters: The validated filters that produced the result.
        findings: Individual findings.
        citations: All citations referenced by observed findings.
        evidence_type: Overall evidence basis of the result.
        disclosure: Disclosure text shown when live data is unavailable.
        trends: Observed or estimated market trends.
        skill_gaps: Skill gaps relative to the user's history.
        recommendations: Actionable recommendations.
    """

    filters: MarketSearchFilters
    findings: list[MarketFinding]
    citations: list[Citation]
    evidence_type: Literal["observed", "estimate"]
    disclosure: str | None = None
    trends: list[str]
    skill_gaps: list[str]
    recommendations: list[str]
