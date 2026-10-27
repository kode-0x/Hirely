"""Skills-loading layer: vendored ResumeSkills markdown and feature mapping.

Reads skill markdown in place from ``.agents/skills/<slug>/SKILL.md`` (cached),
asserts all required slugs exist, and maps each feature to its skill slugs.
"""

from __future__ import annotations

from hirely.skills.loader import (
    REQUIRED_SKILL_SLUGS,
    SkillConfigurationError,
    assert_skills_present,
    load_skill,
)
from hirely.skills.registry import FEATURE_SKILLS, load_feature_skills, skills_for

__all__ = [
    "FEATURE_SKILLS",
    "REQUIRED_SKILL_SLUGS",
    "SkillConfigurationError",
    "assert_skills_present",
    "load_feature_skills",
    "load_skill",
    "skills_for",
]
