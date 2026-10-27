"""Hirely entrypoint: dashboard plus the global provider/model banner.

This is the Streamlit multipage app's home. It renders the Hirely wordmark, a
dashboard that lists the available tools and the selected provider, active
model, and connection status, and the always-visible provider/model indicator
that every page shares. It holds only presentation and session wiring; all
provider HTTP lives in the provider layer.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui

_TOOLS = [
    ("Market Research", "Research the job market first: trends, skill gaps, match score, recommendations."),
    ("Resume Checker", "Upload a resume for prioritized, grounded improvement suggestions."),
    ("Resume Scorer", "Deterministic 0-100 match score with a labeled AI assessment."),
    ("Resume Tailor", "Tailor a resume to a posting with an explained change-set."),
    ("Cover Letter", "Generate a cover letter grounded strictly in your resume."),
    ("Interview Prep", "Likely questions, talking points, and focus areas."),
    ("Salary Negotiation", "Market-rate research and negotiation strategy with honest disclosure."),
    ("Career Coach", "Interactive Q&A using your resume and job-description context."),
    ("Settings", "Choose the provider and model; verify connectivity and free models."),
]


def main() -> None:
    """Render the Hirely dashboard."""
    ui.configure_page("Home")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Hirely")
    st.caption("A zero-cost AI career suite. Research the market first, then build grounded documents.")

    model = ui.active_model(settings)
    col_provider, col_model = st.columns(2)
    with col_provider:
        st.metric("Provider", settings.ai_provider)
    with col_model:
        st.metric("Active model", model or "not selected")

    st.subheader("Workflow")
    st.write(
        "Start with Market Research. Downstream resume tools read that research from your session "
        "and prompt you to run it first if it is missing."
    )

    st.subheader("Tools")
    for name, description in _TOOLS:
        st.markdown(f"**{name}** - {description}")


if __name__ == "__main__":
    main()
else:
    main()
