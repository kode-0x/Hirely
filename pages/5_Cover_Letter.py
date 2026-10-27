"""Cover Letter: generate a grounded cover letter with the validation contract.

Inputs are resume, job description, job title, and company. When any required
input is missing the deterministic validation message is shown and no provider
call is made. Generation supports regenerate, inline edit, copy, and download.
All provider HTTP lives behind the service.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui
from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload
from hirely.providers.base import ProviderError
from hirely.services import CoverLetterValidationError, generate_cover_letter

_BODY_KEY = "cover_letter_body"


def main() -> None:
    """Render the Cover Letter page."""
    ui.configure_page("Cover Letter")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Cover Letter")
    st.caption("Generate a cover letter grounded strictly in your resume.")

    upload = st.file_uploader("Resume (PDF or DOCX)", type=["pdf", "docx"])
    job_description = st.text_area("Job description", height=160)
    col_title, col_company = st.columns(2)
    with col_title:
        job_title = st.text_input("Job title")
    with col_company:
        company = st.text_input("Company")

    model = ui.require_model(settings)
    label = "Regenerate" if _BODY_KEY in st.session_state else "Generate cover letter"

    if st.button(label, type="primary", disabled=model is None):
        if model is None:
            st.stop()

        resume_text = ""
        if upload is not None:
            try:
                media_type = validate_upload(upload, settings)
                resume_text = parse_document(upload, media_type).text
            except (ValidationError, DocumentError) as exc:
                st.error(str(exc))
                st.stop()

        try:
            letter = generate_cover_letter(
                ui.get_provider(settings),
                model=model,
                resume_text=resume_text,
                job_description=job_description,
                job_title=job_title,
                company=company,
            )
        except CoverLetterValidationError as exc:
            st.warning(str(exc))
            st.stop()
        except ProviderError as exc:
            st.error(f"The provider could not generate the cover letter: {exc}")
            st.stop()

        st.session_state[_BODY_KEY] = letter.body

    if _BODY_KEY in st.session_state:
        st.subheader("Cover letter")
        body = st.text_area("Edit as needed", value=st.session_state[_BODY_KEY], height=320, key="cover_letter_edit")
        st.session_state[_BODY_KEY] = body
        st.code(body, language="text")
        st.caption("Use the copy control on the block above to copy the text.")
        st.download_button(
            "Download cover letter",
            data=body,
            file_name="cover-letter.txt",
            mime="text/plain",
        )


main()
