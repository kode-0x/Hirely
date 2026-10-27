"""Deterministic resume scoring plus a labeled AI narrative.

The numeric 0-100 score is computed here by a fixed rubric, never by the AI
model, so it is reproducible and unit-testable:
``score = round(100 * (0.70 * required_coverage + 0.30 * preferred_coverage))``
using ATS keyword matching. Interpretation bands are inclusive lower bounds on
the rounded integer. With no job description the scorer runs a checklist mode
labeled an ATS-readiness estimate. The AI layer contributes only labeled
qualitative evidence and recommendations and never adjusts the number.
"""

from __future__ import annotations

import re
from typing import Literal

from hirely.schemas.scoring import CategoryScore, MatchScore

#: Weight applied to required-skill coverage in the rubric.
REQUIRED_WEIGHT = 0.70

#: Weight applied to preferred-skill coverage in the rubric.
PREFERRED_WEIGHT = 0.30

_TOKEN = re.compile(r"[a-z0-9+#.]+")


def _tokenize(text: str) -> set[str]:
    """Normalize text into a set of lower-case ATS tokens.

    Args:
        text: Free-text resume or skill content.

    Returns:
        The distinct normalized tokens.
    """
    return set(_TOKEN.findall(text.lower()))


def _keyword_present(keyword: str, resume_tokens: set[str], resume_lower: str) -> bool:
    """Decide whether a keyword is covered by the resume.

    A single-word keyword matches on a token; a multi-word keyword matches as a
    normalized substring of the resume text.

    Args:
        keyword: The required or preferred skill keyword.
        resume_tokens: Pre-computed resume tokens.
        resume_lower: The lower-cased resume text for phrase matching.

    Returns:
        ``True`` when the keyword is covered.
    """
    cleaned = keyword.strip().lower()
    if not cleaned:
        return False
    parts = _TOKEN.findall(cleaned)
    if len(parts) <= 1:
        return bool(parts) and parts[0] in resume_tokens
    return cleaned in resume_lower


def _score_category(name: str, keywords: list[str], resume_text: str) -> CategoryScore:
    """Score coverage of one keyword category against the resume.

    Args:
        name: Category name (for example, ``"required"``).
        keywords: The category's keywords.
        resume_text: The resume text.

    Returns:
        The category coverage, with matched and missing keywords. Coverage is
        ``1.0`` for an empty category (nothing to miss).
    """
    unique_keywords = list(dict.fromkeys(k.strip() for k in keywords if k.strip()))
    if not unique_keywords:
        return CategoryScore(name=name, coverage=1.0, matched=[], missing=[])

    resume_tokens = _tokenize(resume_text)
    resume_lower = resume_text.lower()
    matched: list[str] = []
    missing: list[str] = []
    for keyword in unique_keywords:
        if _keyword_present(keyword, resume_tokens, resume_lower):
            matched.append(keyword)
        else:
            missing.append(keyword)

    coverage = len(matched) / len(unique_keywords)
    return CategoryScore(name=name, coverage=coverage, matched=matched, missing=missing)


def band_for(score: int) -> Literal["Excellent", "Strong", "Moderate", "Weak", "Poor"]:
    """Map a rounded integer score to its interpretation band.

    Bands are inclusive lower bounds on the rounded integer: ``>=90``
    Excellent, ``>=75`` Strong, ``>=60`` Moderate, ``>=50`` Weak, else Poor.

    Args:
        score: The rounded integer score in ``[0, 100]``.

    Returns:
        The interpretation band.
    """
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Strong"
    if score >= 60:
        return "Moderate"
    if score >= 50:
        return "Weak"
    return "Poor"


def score_resume(
    resume_text: str,
    *,
    required_skills: list[str],
    preferred_skills: list[str],
    ai_evidence: list[str] | None = None,
    ai_recommendations: list[str] | None = None,
) -> MatchScore:
    """Compute the deterministic match score with optional AI narrative.

    The number is computed solely from keyword coverage; any supplied AI
    evidence or recommendations are carried through as labeled judgment and
    never alter the number.

    Args:
        resume_text: The extracted resume text.
        required_skills: Required skills parsed from the job description.
        preferred_skills: Preferred skills parsed from the job description.
        ai_evidence: Optional labeled AI evidence to carry through.
        ai_recommendations: Optional labeled AI recommendations to carry through.

    Returns:
        The deterministic :class:`MatchScore`.
    """
    required = _score_category("required", required_skills, resume_text)
    preferred = _score_category("preferred", preferred_skills, resume_text)

    score = round(100 * (REQUIRED_WEIGHT * required.coverage + PREFERRED_WEIGHT * preferred.coverage))
    return MatchScore(
        score=score,
        band=band_for(score),
        required=required,
        preferred=preferred,
        ai_evidence=list(ai_evidence or []),
        ai_recommendations=list(ai_recommendations or []),
    )


def ats_readiness(
    resume_text: str,
    *,
    checklist: list[str],
    ai_evidence: list[str] | None = None,
    ai_recommendations: list[str] | None = None,
) -> MatchScore:
    """Score general ATS readiness when no job description is supplied.

    This checklist mode scores the resume against generic ATS-readiness
    heuristics and is labeled as a readiness estimate, not a job match. All
    checklist items are treated as the required category and the preferred
    category is empty.

    Args:
        resume_text: The extracted resume text.
        checklist: Generic ATS-readiness keywords/sections to look for.
        ai_evidence: Optional labeled AI evidence to carry through.
        ai_recommendations: Optional labeled AI recommendations to carry through.

    Returns:
        The deterministic readiness :class:`MatchScore`.
    """
    return score_resume(
        resume_text,
        required_skills=checklist,
        preferred_skills=[],
        ai_evidence=ai_evidence,
        ai_recommendations=ai_recommendations,
    )
