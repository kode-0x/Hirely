"""Interview Prep: render likely questions, guidance, and focus areas.

Produces interview preparation grounded in the resume and, when supplied, the
target job description, and offers a download of the material. All provider HTTP
lives behind the service.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui
from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload
from hirely.providers.base import ProviderError
from hirely.schemas.outputs import InterviewPrep
from hirely.services import prepare_interview


def _format_download(result: InterviewPrep) -> str:
    """Render the interview-prep material as plain text for download.

    Args:
        result: The interview preparation material.

    Returns:
        A plain-text rendering of questions, guidance, and focus areas.
    """
    lines = ["Focus areas:"]
    lines.extend(f"- {area}" for area in result.focus_areas)
    lines.append("")
    lines.append("Questions:")
    for index, question in enumerate(result.questions, start=1):
        lines.append(f"{index}. {question.question}")
        lines.append(f"   Guidance: {question.guidance}")
    return "\n".join(lines)


def main() -> None:
    """Render the Interview Prep page."""
    ui.configure_page("Interview Prep")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Interview Prep")
    st.caption("STAR-ready talking points, likely questions, and focus areas.")

    upload = st.file_uploader("Resume (PDF or DOCX)", type=["pdf", "docx"])
    job_description = st.text_area("Job description (optional)", height=160)
    model = ui.require_model(settings)

    if st.button("Prepare interview material", type="primary", disabled=upload is None or model is None):
        if upload is None or model is None:
            st.stop()
        try:
            media_type = validate_upload(upload, settings)
            document = parse_document(upload, media_type)
        except (ValidationError, DocumentError) as exc:
            st.error(str(exc))
            st.stop()

        try:
            result = prepare_interview(
                ui.get_provider(settings),
                model=model,
                resume_text=document.text,
                job_description=job_description or None,
            )
        except ProviderError as exc:
            st.error(f"The provider could not prepare interview material: {exc}")
            st.stop()

        st.subheader("Focus areas")
        for area in result.focus_areas:
            st.markdown(f"- {area}")

        st.subheader("Likely questions")
        for index, question in enumerate(result.questions, start=1):
            with st.expander(f"{index}. {question.question}"):
                st.write(question.guidance)

        st.download_button(
            "Download interview prep",
            data=_format_download(result),
            file_name="interview-prep.txt",
            mime="text/plain",
        )


main()
