"""Career Coach: interactive Q&A using resume and job-description context.

Answers coaching questions grounded in the supplied resume and optional job
description, and communicates uncertainty rather than fabricating facts. All
provider HTTP lives behind the service.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui
from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload
from hirely.providers.base import ProviderError
from hirely.services import coach


def main() -> None:
    """Render the Career Coach page."""
    ui.configure_page("Career Coach")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Career Coach")
    st.caption("Interactive Q&A grounded in your resume and target role. It is honest about uncertainty.")

    upload = st.file_uploader("Resume (PDF or DOCX, optional)", type=["pdf", "docx"])
    job_description = st.text_area("Job description (optional)", height=140)
    question = st.text_area("Your question", height=120)
    model = ui.require_model(settings)

    ready = bool(question.strip()) and model is not None
    if st.button("Ask the coach", type="primary", disabled=not ready):
        if model is None:
            st.stop()

        resume_text: str | None = None
        if upload is not None:
            try:
                media_type = validate_upload(upload, settings)
                resume_text = parse_document(upload, media_type).text
            except (ValidationError, DocumentError) as exc:
                st.error(str(exc))
                st.stop()

        try:
            result = coach(
                ui.get_provider(settings),
                model=model,
                question=question,
                resume_text=resume_text,
                job_description=job_description or None,
            )
        except ProviderError as exc:
            st.error(f"The provider could not answer: {exc}")
            st.stop()

        st.subheader("Response")
        st.write(result.raw_text)


main()
