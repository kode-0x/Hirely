"""Schemas for feature service outputs.

These typed results are returned by the resume checker, tailor, cover-letter,
interview-prep, and salary-negotiation services and rendered by the pages.
Salary research carries a mandatory disclosure so training-data figures are
never presented as researched rates.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from hirely.schemas.market import Citation


class CheckerResult(BaseModel):
    """Result of an ATS-readiness resume check.

    Attributes:
        strengths: Observed strengths of the resume.
        issues: Detected issues to address.
        suggestions: Concrete improvement suggestions.
    """

    strengths: list[str]
    issues: list[str]
    suggestions: list[str]


class TailorChange(BaseModel):
    """A single tailoring edit with its rationale.

    Attributes:
        section: Resume section the change applies to.
        before: Original text.
        after: Proposed replacement text.
        rationale: Why the change improves the fit.
    """

    section: str
    before: str
    after: str
    rationale: str


class TailorChangeSet(BaseModel):
    """A set of tailoring changes for a specific job posting.

    Attributes:
        changes: Individual edits.
        summary: Summary of how the resume was tailored.
    """

    changes: list[TailorChange]
    summary: str


class CoverLetter(BaseModel):
    """A generated cover letter grounded in verified user input.

    Attributes:
        title: Target job title.
        company: Target company.
        body: The cover-letter text.
    """

    title: str
    company: str
    body: str


class InterviewQuestion(BaseModel):
    """An interview question with preparation guidance.

    Attributes:
        question: The interview question.
        guidance: Suggested approach for answering.
    """

    question: str
    guidance: str


class InterviewPrep(BaseModel):
    """Interview preparation material.

    Attributes:
        questions: Prepared questions with guidance.
        focus_areas: Topics to emphasize during preparation.
    """

    questions: list[InterviewQuestion]
    focus_areas: list[str]


class SalaryResearch(BaseModel):
    """Salary research with mandatory evidence disclosure.

    When no live market data is available the result degrades to estimates
    with empty citations and a disclosure string; researched rates are never
    fabricated from training data.

    Attributes:
        role: The role the research applies to.
        evidence_type: Whether figures are observed or estimated.
        disclosure: Mandatory disclosure about the evidence basis.
        range_low: Optional low end of the salary range.
        range_high: Optional high end of the salary range.
        currency: Optional currency code for the range.
        citations: Sources for observed figures; empty for estimates.
        retrieved_at: Optional date the figures were retrieved.
        talking_points: Negotiation talking points.
    """

    role: str
    evidence_type: Literal["observed", "estimate"]
    disclosure: str
    range_low: float | None = None
    range_high: float | None = None
    currency: str | None = None
    citations: list[Citation] = []
    retrieved_at: date | None = None
    talking_points: list[str] = []
