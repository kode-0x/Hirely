"""Feature services: the engine the Streamlit pages render.

Each service orchestrates parse -> build-prompt -> provider -> schema-validate
and returns a typed result. The resume scorer is deterministic; the cover-letter
service enforces a deterministic validation contract; the salary service
degrades identically to market research when live data is unavailable.
"""

from __future__ import annotations

from hirely.services.career_coach import coach
from hirely.services.cover_letter import CoverLetterValidationError, generate_cover_letter
from hirely.services.interview_prep import prepare_interview
from hirely.services.resume_checker import check_resume
from hirely.services.resume_scorer import ats_readiness, band_for, score_resume
from hirely.services.resume_tailor import tailor_resume
from hirely.services.salary_negotiation import research_salary

__all__ = [
    "CoverLetterValidationError",
    "ats_readiness",
    "band_for",
    "check_resume",
    "coach",
    "generate_cover_letter",
    "prepare_interview",
    "research_salary",
    "score_resume",
    "tailor_resume",
]
