"""Resume checker service.

Produces prioritized improvement suggestions grounded only in the uploaded
resume content. The resume text is placed in the untrusted user channel; the
bullet-writer and quantifier frameworks are supplied as trusted guidance. The
numeric score lives in the scorer service; this service returns qualitative
strengths, issues, and suggestions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hirely.prompts.builder import UserSection, build_messages
from hirely.schemas.outputs import CheckerResult
from hirely.skills.registry import load_feature_skills

if TYPE_CHECKING:
    from hirely.providers.base import AIProvider

_TASK_INSTRUCTION = (
    "Review the resume for ATS readiness and bullet quality. Return prioritized, concrete "
    "suggestions grounded only in the resume content. Do not invent achievements or metrics."
)


def check_resume(provider: AIProvider, *, model: str, resume_text: str) -> CheckerResult:
    """Run an ATS-readiness check over the resume.

    Args:
        provider: The AI provider adapter to call.
        model: The model identifier to use.
        resume_text: The extracted resume text.

    Returns:
        The checker result from the provider, validated against
        :class:`CheckerResult`.

    Raises:
        ProviderError: If the provider call fails or the structured response
            cannot be validated.
    """
    messages = build_messages(
        load_feature_skills("resume_checker"),
        [UserSection("RESUME", resume_text)],
        task_instruction=_TASK_INSTRUCTION,
    )
    result = provider.chat(messages, model=model, response_model=CheckerResult)
    return CheckerResult.model_validate_json(result.raw_text)
