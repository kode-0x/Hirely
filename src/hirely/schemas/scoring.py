"""Schemas for deterministic resume scoring.

The numeric score is computed by a deterministic rubric, not the AI model.
Interpretation bands are inclusive lower bounds on the rounded integer score.
AI output contributes only labeled qualitative evidence and recommendations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CategoryScore(BaseModel):
    """Coverage of one skill category against a resume.

    Attributes:
        name: Category name (for example, "required" or "preferred").
        coverage: Fraction of category items matched, in ``[0, 1]``.
        matched: Items found in the resume.
        missing: Items absent from the resume.
    """

    name: str
    coverage: float = Field(ge=0.0, le=1.0)
    matched: list[str]
    missing: list[str]


class MatchScore(BaseModel):
    """Deterministic match score plus labeled AI narrative.

    Attributes:
        score: Integer score in ``[0, 100]``.
        band: Interpretation band for the score.
        required: Coverage of required skills.
        preferred: Coverage of preferred skills.
        ai_evidence: AI-generated supporting evidence (labeled AI judgment).
        ai_recommendations: AI-generated recommendations (labeled AI judgment).
    """

    score: int = Field(ge=0, le=100)
    band: Literal["Excellent", "Strong", "Moderate", "Weak", "Poor"]
    required: CategoryScore
    preferred: CategoryScore
    ai_evidence: list[str]
    ai_recommendations: list[str]
