"""Salary Negotiation: market-rate research plus negotiation strategy.

Reuses the market-research abstraction, so it degrades identically to Market
Research when live data is unavailable: the same no-network disclosure banner is
shown and estimates are labeled distinctly, never presented as researched
rates. This page holds only widget wiring and rendering.
"""

from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

from hirely import ui
from hirely.schemas.market import MarketSearchFilters
from hirely.schemas.outputs import SalaryResearch
from hirely.services import research_salary

_SENIORITY = ["", "intern", "junior", "mid", "senior", "lead", "principal"]

_DEFAULT_TALKING_POINTS = [
    "Anchor on the role's scope and your demonstrated impact, not on your current pay.",
    "Ask for the budgeted range before naming a number.",
    "Negotiate the full package: base, bonus, equity, and start date.",
]


def _render_result(result: SalaryResearch) -> None:
    """Render salary research, labeling estimates and disclosing their basis.

    Args:
        result: The salary research result.
    """
    if result.evidence_type == "estimate":
        ui.render_no_data_disclosure()
        st.info("The figures and strategy below are model estimates, not researched market rates.")
    else:
        st.caption(result.disclosure)

    st.subheader("Market rate")
    if result.range_low is not None and result.range_high is not None:
        currency = result.currency or ""
        st.write(f"Observed range: {currency} {result.range_low:,.0f} to {result.range_high:,.0f}".strip())
    else:
        st.write("No researched salary range is available for this role.")

    if result.citations:
        st.subheader("Sources")
        for citation in result.citations:
            st.markdown(f"- {citation.source_url} (retrieved {citation.retrieved_at})")

    st.subheader("Negotiation talking points")
    for point in result.talking_points:
        st.markdown(f"- {point}")


def main() -> None:
    """Render the Salary Negotiation page."""
    ui.configure_page("Salary Negotiation")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Salary Negotiation")
    st.caption("Market-rate research and negotiation strategy with honest disclosure.")

    if not settings.market_search_enabled or settings.market_search_endpoint is None:
        ui.render_no_data_disclosure()

    role = st.text_input("Target role", placeholder="e.g. Backend Engineer")
    col_a, col_b = st.columns(2)
    with col_a:
        location = st.text_input("Location", placeholder="e.g. Remote, Berlin")
    with col_b:
        seniority = st.selectbox("Seniority", _SENIORITY, index=0)

    if st.button("Research salary", type="primary"):
        try:
            filters = MarketSearchFilters(
                role=role,
                location=location or None,
                seniority=seniority or None,
            )
        except ValidationError as exc:
            st.error(f"Please fix the inputs: {exc.errors()[0]['msg']}")
            st.stop()

        result = research_salary(filters, settings, talking_points=_DEFAULT_TALKING_POINTS)
        _render_result(result)


main()
