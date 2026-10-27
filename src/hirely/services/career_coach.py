"""Career-coach service.

Runs interactive Q&A using the resume and optional job-description context. It
composes the job-description-analyzer and interview-prep-generator frameworks
as trusted guidance and is honest about uncertainty: it must not fabricate
market facts or resume content. Resume, job description, and the conversation
turns are all placed in the untrusted user channel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.prompts.builder import UserSection, build_messages
from hirely.schemas.provider import ChatResult
from hirely.skills.registry import load_feature_skills

if TYPE_CHECKING:
    from hirely.providers.base import AIProvider

_TASK_INSTRUCTION = (
    "Act as a career coach. Answer the user's question using only the provided resume and "
    "context. Be explicit about uncertainty; do not fabricate market facts, achievements, or "
    "experience the content does not support."
)


def coach(
    provider: AIProvider,
    *,
    model: str,
    question: str,
    resume_text: str | None = None,
    job_description: str | None = None,
) -> ChatResult:
    """Answer a career-coaching question grounded in the supplied context.

    Args:
        provider: The AI provider adapter to call.
        model: The model identifier to use.
        question: The user's coaching question (untrusted).
        resume_text: Optional resume context.
        job_description: Optional job-description context.

    Returns:
        The provider chat result carrying the coach's answer.

    Raises:
        ProviderError: If the provider call fails.
    """
    sections: list[UserSection] = []
    if resume_text and resume_text.strip():
        sections.append(UserSection("RESUME", resume_text))
    if job_description and job_description.strip():
        sections.append(UserSection("JOB DESCRIPTION", job_description))
    sections.append(UserSection("QUESTION", question))

    messages = build_messages(
        load_feature_skills("career_coach"),
        sections,
        task_instruction=_TASK_INSTRUCTION,
    )
    return provider.chat(messages, model=model)
