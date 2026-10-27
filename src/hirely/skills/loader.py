"""Load vendored ResumeSkills framework markdown.

Skills are read in place from ``.agents/skills/<slug>/SKILL.md`` so the vendored
source stays canonical and license-traceable; they are never copied into the
package. Loaded content is cached for the process lifetime with
:func:`functools.lru_cache` because the markdown is static. A registry check
asserts every required slug exists and raises a clear configuration error when
one is missing.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

#: The eight ResumeSkills slugs vendored for the feature services.
REQUIRED_SKILL_SLUGS: tuple[str, ...] = (
    "job-description-analyzer",
    "resume-ats-optimizer",
    "resume-bullet-writer",
    "resume-quantifier",
    "resume-tailor",
    "cover-letter-generator",
    "interview-prep-generator",
    "salary-negotiation-prep",
)


class SkillConfigurationError(Exception):
    """A required skill markdown file is missing or unreadable.

    Raised at startup by :func:`assert_skills_present` and by
    :func:`load_skill` when a slug's ``SKILL.md`` cannot be found.
    """


def _skills_root() -> Path:
    """Return the on-disk root of the vendored skills.

    The root is ``.agents/skills`` relative to the repository, resolved from
    this module's location (``src/hirely/skills/loader.py`` -> three parents to
    the repo root).

    Returns:
        The absolute path to the skills directory.
    """
    return Path(__file__).resolve().parents[3] / ".agents" / "skills"


@cache
def load_skill(slug: str) -> str:
    """Load and cache the markdown for a single skill.

    Args:
        slug: The skill directory name under ``.agents/skills``.

    Returns:
        The full text of the skill's ``SKILL.md``.

    Raises:
        SkillConfigurationError: If the skill's ``SKILL.md`` does not exist.
    """
    path = _skills_root() / slug / "SKILL.md"
    if not path.is_file():
        raise SkillConfigurationError(f"Missing skill definition: {slug}/SKILL.md")
    return path.read_text(encoding="utf-8")


def assert_skills_present() -> None:
    """Assert every required skill slug is present on disk.

    Intended to run once at startup so a misconfigured deployment fails fast
    with a clear message rather than at first feature use.

    Raises:
        SkillConfigurationError: If any required slug's ``SKILL.md`` is missing.
    """
    root = _skills_root()
    missing = [slug for slug in REQUIRED_SKILL_SLUGS if not (root / slug / "SKILL.md").is_file()]
    if missing:
        joined = ", ".join(sorted(missing))
        raise SkillConfigurationError(f"Missing required skill definitions: {joined}")
