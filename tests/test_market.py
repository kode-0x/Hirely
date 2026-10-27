"""Market-research tests.

Covers filter pass-through for all five filters, future-date rejection, dedup
and stale detection, and the no-network disclosure path for both Market
Research and Salary. All backends are in-memory fakes; no network is touched.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import HttpUrl, ValidationError

from hirely.config import Settings
from hirely.market.dedup import classify_freshness, deduplicate
from hirely.market.research import NO_DATA_DISCLOSURE, run_market_research
from hirely.market.websearch import FetchedPage, NullBackend, RawPosting
from hirely.schemas.market import MarketSearchFilters
from hirely.services.salary_negotiation import research_salary
from tests.conftest import RecordingWebFetch, RecordingWebSearch


def _enabled_settings() -> Settings:
    return Settings(
        ai_provider="ollama",
        market_search_enabled=True,
        market_search_endpoint="https://search.example.test/api",
    )


def _disabled_settings() -> Settings:
    return Settings(ai_provider="ollama", market_search_enabled=False)


# --- Filter validation (all five filters + future-date rejection) -----------


def test_all_five_filters_validated_and_passed_through() -> None:
    filters = MarketSearchFilters(
        role="Backend Engineer",
        location="Remote",
        industry="Fintech",
        seniority="senior",
        date_from=date(2024, 1, 1),
    )
    search = RecordingWebSearch(configured=True)
    fetch = RecordingWebFetch()
    run_market_research(filters, _enabled_settings(), search=search, fetch=fetch)
    assert len(search.calls) == 1
    call = search.calls[0]
    assert call["role"] == "Backend Engineer"
    assert call["location"] == "Remote"
    assert call["industry"] == "Fintech"
    assert call["seniority"] == "senior"
    assert call["date_from"] == date(2024, 1, 1)


def test_future_date_from_is_rejected() -> None:
    future = date.today() + timedelta(days=5)
    with pytest.raises(ValidationError):
        MarketSearchFilters(role="Engineer", date_from=future)


def test_blank_role_rejected() -> None:
    with pytest.raises(ValidationError):
        MarketSearchFilters(role="   ")


# --- Dedup and stale detection ----------------------------------------------


def test_deduplicate_removes_matching_postings() -> None:
    a = RawPosting(title="Eng", company="Acme", location="Remote", url="https://x.test/job?ref=1")
    b = RawPosting(title="eng", company="ACME", location="remote", url="https://x.test/job?ref=2")
    c = RawPosting(title="Eng", company="Other", url="https://y.test/job")
    unique = deduplicate([a, b, c])
    assert len(unique) == 2


def test_classify_freshness_stale_fresh_unknown() -> None:
    today = date(2024, 6, 1)
    assert classify_freshness(None, 45, today=today) == "unknown"
    assert classify_freshness(today - timedelta(days=10), 45, today=today) == "fresh"
    assert classify_freshness(today - timedelta(days=90), 45, today=today) == "stale"


# --- No-network disclosure (Market + Salary) --------------------------------


def test_market_disabled_returns_disclosure_estimate() -> None:
    filters = MarketSearchFilters(role="Engineer")
    result = run_market_research(filters, _disabled_settings())
    assert result.evidence_type == "estimate"
    assert result.citations == []
    assert result.disclosure == NO_DATA_DISCLOSURE
    assert result.findings == []


def test_market_null_backend_falls_back_to_disclosure() -> None:
    filters = MarketSearchFilters(role="Engineer")
    null = NullBackend()
    result = run_market_research(filters, _enabled_settings(), search=null, fetch=null)
    assert result.evidence_type == "estimate"
    assert result.disclosure == NO_DATA_DISCLOSURE


def test_market_observed_path_produces_citation() -> None:
    filters = MarketSearchFilters(role="Engineer")
    posting = RawPosting(title="Backend Engineer", company="Acme", url="https://acme.test/job/1")
    page = FetchedPage(url="https://acme.test/job/1", text="JD text", retrieved_at=date.today())
    search = RecordingWebSearch([posting], configured=True)
    fetch = RecordingWebFetch({"https://acme.test/job/1": page})
    result = run_market_research(filters, _enabled_settings(), search=search, fetch=fetch)
    assert result.evidence_type == "observed"
    assert len(result.citations) == 1
    assert result.citations[0].source_url == HttpUrl("https://acme.test/job/1")


def test_salary_degrades_to_estimate_with_disclosure() -> None:
    filters = MarketSearchFilters(role="Engineer")
    salary = research_salary(filters, _disabled_settings())
    assert salary.evidence_type == "estimate"
    assert salary.citations == []
    assert salary.disclosure == NO_DATA_DISCLOSURE
    assert salary.range_low is None and salary.range_high is None
