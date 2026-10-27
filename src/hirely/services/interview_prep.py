"""Interview preparation service.

Produces STAR-style stories, likely questions, and talking points grounded in
the user's resume and, when supplied, the target job description. User content
is placed in the untrusted channel; the interview-prep framework is supplied as
trusted guidance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.prompts.builder import UserSection, build_messages
from hirely.schemas.outputs import InterviewPrep
from hirely.skills.registry import load_feature_skills

if TYPE_CHECKING:
    from hirely.providers.base import AIProvider

_TASK_INSTRUCTION = (
    "Prepare interview material grounded in the resume. Produce likely questions with guidance "
    "and focus areas. Base every example on the resume; do not invent experience."
)


def prepare_interview(
    provider: AIProvider,
    *,
    model: str,
    resume_text: str,
    job_description: str | None = None,
) -> InterviewPrep:
    """Generate interview preparation material.

    Args:
        provider: The AI provider adapter to call.
        model: The model identifier to use.
        resume_text: The user's resume text.
        job_description: Optional target job description for focus areas.

    Returns:
        The interview-prep material, validated against :class:`InterviewPrep`.

    Raises:
        ProviderError: If the provider call fails or the structured response
            cannot be validated.
    """
    sections = [UserSection("RESUME", resume_text)]
    if job_description and job_description.strip():
        sections.append(UserSection("JOB DESCRIPTION", job_description))

    messages = build_messages(
        load_feature_skills("interview_prep"),
        sections,
        task_instruction=_TASK_INSTRUCTION,
    )
    result = provider.chat(messages, model=model, response_model=InterviewPrep)
    return InterviewPrep.model_validate_json(result.raw_text)
