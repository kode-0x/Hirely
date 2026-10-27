"""Resume Checker: upload a resume and render prioritized improvement findings.

Validates and parses the uploaded PDF/DOCX, runs the resume-checker service,
and renders strengths, issues, and prioritized suggestions with distinct
success/warning/error states. All provider HTTP lives behind the service; this
page issues none.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui
from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload
from hirely.providers.base import ProviderError
from hirely.services import check_resume


def _render_result(strengths: list[str], issues: list[str], suggestions: list[str]) -> None:
    """Render the checker output in prioritized sections.

    Args:
        strengths: Observed resume strengths.
        issues: Detected issues to address.
        suggestions: Concrete, prioritized suggestions.
    """
    st.subheader("Prioritized suggestions")
    if suggestions:
        for index, suggestion in enumerate(suggestions, start=1):
            st.markdown(f"{index}. {suggestion}")
    else:
        st.write("No suggestions returned.")

    st.subheader("Issues and missing or weak sections")
    if issues:
        for issue in issues:
            st.markdown(f"- {issue}")
    else:
        st.success("No blocking issues detected.")

    st.subheader("Strengths")
    for strength in strengths:
        st.markdown(f"- {strength}")


def main() -> None:
    """Render the Resume Checker page."""
    ui.configure_page("Resume Checker")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Resume Checker")
    st.caption("Upload a resume for prioritized, grounded improvement suggestions.")

    upload = st.file_uploader("Resume (PDF or DOCX)", type=["pdf", "docx"])
    model = ui.require_model(settings)

    if st.button("Check resume", type="primary", disabled=upload is None or model is None):
        if upload is None or model is None:
            st.stop()
        try:
            media_type = validate_upload(upload, settings)
            document = parse_document(upload, media_type)
        except (ValidationError, DocumentError) as exc:
            st.error(str(exc))
            st.stop()

        try:
            result = check_resume(ui.get_provider(settings), model=model, resume_text=document.text)
        except ProviderError as exc:
            st.error(f"The provider could not complete the check: {exc}")
            st.stop()

        _render_result(result.strengths, result.issues, result.suggestions)


main()
