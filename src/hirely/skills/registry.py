"""Feature-to-skill mapping.

Each feature service composes one or more ResumeSkills frameworks into the
trusted system channel of its prompt. Career Coach composes the
job-description-analyzer and interview-prep-generator skills when context is
supplied; Market Research uses no ResumeSkills skill because it gathers
evidence rather than authoring documents.
"""

from __future__ import annotations

from hirely.skills.loader import load_skill

#: Feature key -> ordered list of ResumeSkills slugs.
FEATURE_SKILLS: dict[str, tuple[str, ...]] = {
    "resume_scorer": ("job-description-analyzer", "resume-ats-optimizer"),
    "job_match": ("job-description-analyzer", "resume-ats-optimizer"),
    "resume_checker": ("resume-bullet-writer", "resume-quantifier"),
    "resume_tailor": ("resume-tailor",),
    "cover_letter": ("cover-letter-generator",),
    "interview_prep": ("interview-prep-generator",),
    "salary_negotiation": ("salary-negotiation-prep",),
    "career_coach": ("job-description-analyzer", "interview-prep-generator"),
    "market_research": (),
}


def skills_for(feature: str) -> tuple[str, ...]:
    """Return the skill slugs mapped to a feature.

    Args:
        feature: A feature key from :data:`FEATURE_SKILLS`.

    Returns:
        The ordered slugs for the feature; empty for features that use none.

    Raises:
        KeyError: If the feature key is unknown.
    """
    return FEATURE_SKILLS[feature]


def load_feature_skills(feature: str) -> list[str]:
    """Load the markdown for every skill mapped to a feature.

    Args:
        feature: A feature key from :data:`FEATURE_SKILLS`.

    Returns:
        The loaded skill markdown in mapping order; empty for features that use
        no skill.

    Raises:
        KeyError: If the feature key is unknown.
        SkillConfigurationError: If a mapped skill's ``SKILL.md`` is missing.
    """
    return [load_skill(slug) for slug in skills_for(feature)]
