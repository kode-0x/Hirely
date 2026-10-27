"""Deterministic scoring tests: the 70/30 rubric, every band edge, and the
heuristic-vs-AI separation.
"""

from __future__ import annotations

import pytest

from hirely.services.resume_scorer import band_for, score_resume


def test_rubric_math_full_coverage() -> None:
    result = score_resume("python docker", required_skills=["python"], preferred_skills=["docker"])
    # 0.70*1 + 0.30*1 = 1.0 -> 100
    assert result.score == 100
    assert result.band == "Excellent"


def test_rubric_math_required_only() -> None:
    result = score_resume("python", required_skills=["python"], preferred_skills=["docker"])
    # 0.70*1 + 0.30*0 = 0.70 -> 70
    assert result.score == 70
    assert result.band == "Moderate"


def test_rubric_math_preferred_only() -> None:
    result = score_resume("docker", required_skills=["python"], preferred_skills=["docker"])
    # 0.70*0 + 0.30*1 = 0.30 -> 30
    assert result.score == 30
    assert result.band == "Poor"


def test_multiword_keyword_matches_as_phrase() -> None:
    result = score_resume(
        "experience with amazon web services and more",
        required_skills=["amazon web services"],
        preferred_skills=[],
    )
    assert result.score == 100
    assert result.required.matched == ["amazon web services"]


def test_empty_category_counts_as_full_coverage() -> None:
    result = score_resume("anything", required_skills=[], preferred_skills=[])
    assert result.required.coverage == 1.0
    assert result.preferred.coverage == 1.0
    assert result.score == 100


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (100, "Excellent"),
        (90, "Excellent"),
        (89, "Strong"),
        (75, "Strong"),
        (74, "Moderate"),
        (60, "Moderate"),
        (59, "Weak"),
        (50, "Weak"),
        (49, "Poor"),
        (0, "Poor"),
    ],
)
def test_band_edges_are_inclusive_lower_bounds(score: int, band: str) -> None:
    assert band_for(score) == band


def test_ai_narrative_never_changes_number() -> None:
    base = score_resume("python", required_skills=["python", "go"], preferred_skills=[])
    with_ai = score_resume(
        "python",
        required_skills=["python", "go"],
        preferred_skills=[],
        ai_evidence=["looks strong on python"],
        ai_recommendations=["learn go"],
    )
    assert base.score == with_ai.score
    assert with_ai.ai_evidence == ["looks strong on python"]
    assert with_ai.ai_recommendations == ["learn go"]
