"""Resume Scorer and Job-Match on a single page.

Renders the deterministic 0-100 score, its interpretation band, and per-category
coverage in one block, and labeled AI evidence/recommendations in a visually
distinct "AI assessment" block. With a job description supplied this is a job
match; without one it is a general ATS-readiness estimate. The page never claims
to predict hiring or guarantee ATS pass-through.

The numeric score is computed deterministically by the scorer service; the page
holds only widget wiring and rendering.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui
from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload
from hirely.schemas.scoring import MatchScore
from hirely.services import ats_readiness, score_resume

#: Generic ATS-readiness checklist used when no job description is supplied.
_ATS_CHECKLIST = [
    "experience",
    "education",
    "skills",
    "summary",
    "achievements",
    "email",
    "phone",
]


def _split_skills(raw: str) -> list[str]:
    """Split a newline/comma-separated skills box into a clean list.

    Args:
        raw: The raw text-area content.

    Returns:
        The non-empty, stripped skill entries.
    """
    tokens: list[str] = []
    for line in raw.replace(",", "\n").splitlines():
        cleaned = line.strip()
        if cleaned:
            tokens.append(cleaned)
    return tokens


def _render_score(result: MatchScore, *, is_match: bool) -> None:
    """Render the deterministic score block and the labeled AI block.

    Args:
        result: The deterministic match score.
        is_match: Whether a job description was supplied (job match vs estimate).
    """
    heading = "Job match score" if is_match else "ATS readiness estimate"
    st.subheader(heading)
    st.caption(
        "This is a deterministic keyword-coverage score. It does not predict hiring outcomes "
        "or guarantee ATS pass-through."
    )
    col_score, col_band = st.columns(2)
    with col_score:
        st.metric("Score (0-100)", result.score)
    with col_band:
        st.metric("Band", result.band)

    st.markdown("**Required coverage**")
    st.progress(result.required.coverage)
    st.write(f"Matched: {', '.join(result.required.matched) or 'none'}")
    st.write(f"Missing: {', '.join(result.required.missing) or 'none'}")

    if is_match:
        st.markdown("**Preferred coverage**")
        st.progress(result.preferred.coverage)
        st.write(f"Matched: {', '.join(result.preferred.matched) or 'none'}")
        st.write(f"Missing: {', '.join(result.preferred.missing) or 'none'}")

    st.subheader("AI assessment")
    st.caption("Labeled AI judgment. It never changes the numeric score above.")
    if result.ai_evidence:
        st.markdown("**Evidence**")
        for item in result.ai_evidence:
            st.markdown(f"- {item}")
    if result.ai_recommendations:
        st.markdown("**Recommendations**")
        for item in result.ai_recommendations:
            st.markdown(f"- {item}")
    if not result.ai_evidence and not result.ai_recommendations:
        st.write("No AI assessment supplied.")


def main() -> None:
    """Render the Resume Scorer / Job-Match page."""
    ui.configure_page("Resume Scorer")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Resume Scorer and Job Match")
    st.caption("Deterministic 0-100 scoring with a labeled AI assessment.")

    upload = st.file_uploader("Resume (PDF or DOCX)", type=["pdf", "docx"])
    st.markdown("Provide a job description to run a job match, or leave it blank for an ATS-readiness estimate.")
    required_raw = st.text_area("Required skills (one per line or comma-separated)", height=120)
    preferred_raw = st.text_area("Preferred skills (one per line or comma-separated)", height=120)

    if st.button("Score resume", type="primary", disabled=upload is None):
        if upload is None:
            st.stop()
        try:
            media_type = validate_upload(upload, settings)
            document = parse_document(upload, media_type)
        except (ValidationError, DocumentError) as exc:
            st.error(str(exc))
            st.stop()

        required = _split_skills(required_raw)
        preferred = _split_skills(preferred_raw)
        is_match = bool(required or preferred)
        if is_match:
            result = score_resume(document.text, required_skills=required, preferred_skills=preferred)
        else:
            result = ats_readiness(document.text, checklist=_ATS_CHECKLIST)
        _render_score(result, is_match=is_match)


main()
