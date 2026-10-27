"""Cover-letter generation with a deterministic validation contract.

Before any provider call, required inputs are validated deterministically: if
the resume, job description, job title, or company is missing (empty after
stripping), a :class:`CoverLetterValidationError` is raised and no provider
call is made. Only when all four inputs are present is the two-channel prompt
built and the provider invoked. Regenerate, edit, copy, and download are
UI-layer concerns that reuse this service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.prompts.builder import UserSection, build_messages
from hirely.schemas.outputs import CoverLetter
from hirely.skills.registry import load_feature_skills

if TYPE_CHECKING:
    from hirely.providers.base import AIProvider

_TASK_INSTRUCTION = (
    "Write a concise, professional cover letter for the target role at the target company. "
    "Ground every claim strictly in the provided resume; do not invent experience or metrics."
)


class CoverLetterValidationError(Exception):
    """A required cover-letter input was missing.

    Raised before any provider call so a missing resume, job description, job
    title, or company never results in a billable request.
    """


def _require(value: str, field_name: str) -> str:
    """Return a stripped non-empty value or raise the validation error.

    Args:
        value: The candidate input value.
        field_name: Human-readable field name for the error message.

    Returns:
        The stripped value.

    Raises:
        CoverLetterValidationError: If the value is empty after stripping.
    """
    cleaned = (value or "").strip()
    if not cleaned:
        raise CoverLetterValidationError(f"{field_name} is required to generate a cover letter.")
    return cleaned


def generate_cover_letter(
    provider: AIProvider,
    *,
    model: str,
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
) -> CoverLetter:
    """Generate a cover letter after validating all required inputs.

    Args:
        provider: The AI provider adapter to call.
        model: The model identifier to use.
        resume_text: The user's resume text.
        job_description: The target job description.
        job_title: The target job title.
        company: The target company.

    Returns:
        The generated cover letter.

    Raises:
        CoverLetterValidationError: If resume, job description, title, or
            company is missing; no provider call is made in that case.
        ProviderError: If the provider call fails.
    """
    resume = _require(resume_text, "Resume")
    jd = _require(job_description, "Job description")
    title = _require(job_title, "Job title")
    org = _require(company, "Company")

    messages = build_messages(
        load_feature_skills("cover_letter"),
        [
            UserSection("RESUME", resume),
            UserSection("JOB DESCRIPTION", jd),
            UserSection("JOB TITLE", title),
            UserSection("COMPANY", org),
        ],
        task_instruction=_TASK_INSTRUCTION,
    )
    result = provider.chat(messages, model=model)
    return CoverLetter(title=title, company=org, body=result.raw_text)
