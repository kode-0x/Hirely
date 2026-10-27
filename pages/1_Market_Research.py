"""Market Research: the core-workflow surface, rendered before any resume work.

Collects the search filters and optional career history, runs the market
research flow, and renders trends, skill gaps, a match score, and
recommendations before any resume is generated or tailored. The result
is stored in session state so downstream pages can gate on it. When live search
is disabled or unavailable, the shared no-network disclosure banner is shown and
no training-data figures are presented as researched rates.

This page holds only widget wiring and rendering. All web HTTP lives in the
market layer behind the research service; this file issues no HTTP itself.
"""

from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

from hirely import ui
from hirely.market.research import run_market_research
from hirely.schemas.market import MarketResearchResult, MarketSearchFilters

_SENIORITY = ["", "intern", "junior", "mid", "senior", "lead", "principal"]


def _collect_filters() -> MarketSearchFilters | None:
    """Collect and validate the market-research filters from the form.

    Returns:
        The validated filters, or ``None`` when validation fails (an error is
        rendered in that case).
    """
    role = st.text_input("Target role", placeholder="e.g. Backend Engineer")
    col_a, col_b = st.columns(2)
    with col_a:
        location = st.text_input("Location", placeholder="e.g. Remote, Berlin")
        seniority = st.selectbox("Seniority", _SENIORITY, index=0)
    with col_b:
        industry = st.text_input("Industry", placeholder="e.g. Fintech")
        date_from = st.date_input("Postings on or after", value=None)

    try:
        return MarketSearchFilters(
            role=role,
            location=location or None,
            industry=industry or None,
            seniority=seniority or None,
            date_from=date_from or None,
        )
    except ValidationError as exc:
        st.error(f"Please fix the filters: {exc.errors()[0]['msg']}")
        return None


def _render_result(result: MarketResearchResult) -> None:
    """Render trends, skill gaps, match score, and recommendations.

    Args:
        result: The market-research result to display.
    """
    if result.evidence_type == "estimate":
        ui.render_no_data_disclosure()

    st.subheader("Trends")
    if result.trends:
        for trend in result.trends:
            st.markdown(f"- {trend}")
    else:
        st.write("No observed trends available.")

    st.subheader("Skill gaps")
    if result.skill_gaps:
        for gap in result.skill_gaps:
            st.markdown(f"- {gap}")
    else:
        st.write("No skill gaps identified.")

    st.subheader("Findings")
    if result.findings:
        for finding in result.findings:
            source = str(finding.citation.source_url) if finding.citation else "no source"
            st.markdown(f"- **{finding.category}**: {finding.value} ({finding.evidence_type}, {source})")
    else:
        st.write("No findings available.")

    st.subheader("Recommendations")
    if result.recommendations:
        for recommendation in result.recommendations:
            st.markdown(f"- {recommendation}")
    else:
        st.write("No recommendations available.")


def main() -> None:
    """Render the Market Research page."""
    ui.configure_page("Market Research")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Market Research")
    st.caption("Research the job market before creating or tailoring a resume.")

    if not settings.market_search_enabled or settings.market_search_endpoint is None:
        ui.render_no_data_disclosure()

    filters = _collect_filters()
    st.text_area("Resume or career history (optional context)", key="mr_history", height=160)

    if st.button("Run market research", type="primary"):
        if filters is None:
            st.stop()
        result = run_market_research(filters, settings)
        ui.store_research(result)
        st.success("Research complete. Downstream resume tools can now use these findings.")

    stored = ui.get_research()
    if stored is not None:
        _render_result(stored)


main()
