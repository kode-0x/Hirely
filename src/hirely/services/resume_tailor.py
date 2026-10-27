"""Resume tailoring service.

Produces a change-set in which each change carries an explanation, grounded
strictly in the source resume and the target job description. The source resume
and job description are placed in the untrusted user channel; the resume-tailor
framework is supplied as trusted guidance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.prompts.builder import UserSection, build_messages
from hirely.schemas.outputs import TailorChangeSet
from hirely.skills.registry import load_feature_skills

if TYPE_CHECKING:
    from hirely.providers.base import AIProvider

_TASK_INSTRUCTION = (
    "Tailor the resume to the job description. Propose a change-set where each change has a "
    "before, an after, and a rationale. Every change must be grounded strictly in the source "
    "resume; never invent experience, metrics, or skills the resume does not support."
)


def tailor_resume(
    provider: AIProvider,
    *,
    model: str,
    resume_text: str,
    job_description: str,
) -> TailorChangeSet:
    """Generate a tailoring change-set for a specific job description.

    Args:
        provider: The AI provider adapter to call.
        model: The model identifier to use.
        resume_text: The source resume text.
        job_description: The target job description.

    Returns:
        The tailoring change-set, validated against :class:`TailorChangeSet`.

    Raises:
        ProviderError: If the provider call fails or the structured response
            cannot be validated.
    """
    messages = build_messages(
        load_feature_skills("resume_tailor"),
        [
            UserSection("RESUME", resume_text),
            UserSection("JOB DESCRIPTION", job_description),
        ],
        task_instruction=_TASK_INSTRUCTION,
    )
    result = provider.chat(messages, model=model, response_model=TailorChangeSet)
    return TailorChangeSet.model_validate_json(result.raw_text)
