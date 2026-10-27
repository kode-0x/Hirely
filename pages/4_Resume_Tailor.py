"""Resume Tailor: tailor a resume to a posting and explain every change.

Lists each proposed change with its rationale and offers a download of the
change-set summary. Gated on the core workflow: the user is prompted to run
Market Research first if no research is stored. All provider HTTP lives behind
the service.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui
from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload
from hirely.providers.base import ProviderError
from hirely.schemas.outputs import TailorChangeSet
from hirely.services import tailor_resume


def _format_download(result: TailorChangeSet) -> str:
    """Render the change-set as plain text for download.

    Args:
        result: The tailoring change-set.

    Returns:
        A plain-text rendering of the summary and each change.
    """
    lines = [f"Summary: {result.summary}", ""]
    for index, change in enumerate(result.changes, start=1):
        lines.append(f"Change {index} [{change.section}]")
        lines.append(f"  Before: {change.before}")
        lines.append(f"  After: {change.after}")
        lines.append(f"  Rationale: {change.rationale}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Render the Resume Tailor page."""
    ui.configure_page("Resume Tailor")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Resume Tailor")
    st.caption("Tailor a resume to a specific posting with an explained change-set.")

    if ui.require_research() is None:
        st.stop()

    upload = st.file_uploader("Resume (PDF or DOCX)", type=["pdf", "docx"])
    job_description = st.text_area("Job description", height=200)
    model = ui.require_model(settings)

    ready = upload is not None and bool(job_description.strip()) and model is not None
    if st.button("Tailor resume", type="primary", disabled=not ready):
        if upload is None or model is None:
            st.stop()
        try:
            media_type = validate_upload(upload, settings)
            document = parse_document(upload, media_type)
        except (ValidationError, DocumentError) as exc:
            st.error(str(exc))
            st.stop()

        try:
            result = tailor_resume(
                ui.get_provider(settings),
                model=model,
                resume_text=document.text,
                job_description=job_description,
            )
        except ProviderError as exc:
            st.error(f"The provider could not tailor the resume: {exc}")
            st.stop()

        st.subheader("Summary")
        st.write(result.summary)

        st.subheader("Changes")
        for index, change in enumerate(result.changes, start=1):
            with st.expander(f"Change {index}: {change.section}"):
                st.markdown(f"**Before:** {change.before}")
                st.markdown(f"**After:** {change.after}")
                st.markdown(f"**Rationale:** {change.rationale}")

        st.download_button(
            "Download change-set",
            data=_format_download(result),
            file_name="resume-tailor-changes.txt",
            mime="text/plain",
        )


main()
