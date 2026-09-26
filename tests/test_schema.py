"""
Unit tests for Pydantic MatchResult schema validation.
"""

import pytest
from pydantic import ValidationError
from models import MatchResult, get_fallback_result


def test_valid_match_result():
    """Test valid MatchResult instance creation."""
    data = {
        "match_score": 85,
        "top_strengths": ["Python expertise", "Generative AI experience"],
        "missing_skills": ["Kubernetes"],
        "summary": "Candidate demonstrates strong alignment with core role requirements.\nMissing container orchestration experience."
    }
    result = MatchResult(**data)
    assert result.match_score == 85
    assert len(result.top_strengths) == 2
    assert len(result.missing_skills) == 1
    assert len(result.summary.splitlines()) == 2


def test_invalid_match_score_above_100():
    """Test match_score > 100 raises ValidationError."""
    data = {
        "match_score": 105,
        "top_strengths": ["Python"],
        "missing_skills": ["SQL"],
        "summary": "Line one.\nLine two."
    }
    with pytest.raises(ValidationError) as exc_info:
        MatchResult(**data)
    assert "match_score" in str(exc_info.value)


def test_invalid_match_score_below_zero():
    """Test match_score < 0 raises ValidationError."""
    data = {
        "match_score": -10,
        "top_strengths": ["Python"],
        "missing_skills": ["SQL"],
        "summary": "Line one.\nLine two."
    }
    with pytest.raises(ValidationError) as exc_info:
        MatchResult(**data)
    assert "match_score" in str(exc_info.value)


def test_invalid_summary_line_count():
    """Test summary with single line or 3 lines raises ValidationError."""
    # Single line
    data_single = {
        "match_score": 50,
        "top_strengths": ["Python"],
        "missing_skills": ["SQL"],
        "summary": "Only one single line summary here."
    }
    with pytest.raises(ValidationError) as exc_info:
        MatchResult(**data_single)
    assert "Summary must contain exactly 2 non-empty lines" in str(exc_info.value)

    # Three lines
    data_triple = {
        "match_score": 50,
        "top_strengths": ["Python"],
        "missing_skills": ["SQL"],
        "summary": "First line.\nSecond line.\nThird line."
    }
    with pytest.raises(ValidationError) as exc_info:
        MatchResult(**data_triple)
    assert "Summary must contain exactly 2 non-empty lines" in str(exc_info.value)


def test_invalid_list_lengths():
    """Test list length boundaries (<1 or >5)."""
    # Empty top_strengths
    data_empty_list = {
        "match_score": 50,
        "top_strengths": [],
        "missing_skills": ["SQL"],
        "summary": "Line one.\nLine two."
    }
    with pytest.raises(ValidationError):
        MatchResult(**data_empty_list)

    # More than 5 items
    data_too_many = {
        "match_score": 50,
        "top_strengths": ["S1", "S2", "S3", "S4", "S5", "S6"],
        "missing_skills": ["M1"],
        "summary": "Line one.\nLine two."
    }
    with pytest.raises(ValidationError):
        MatchResult(**data_too_many)


def test_reject_extra_fields():
    """Test extra unexpected fields are forbidden."""
    data_extra = {
        "match_score": 70,
        "top_strengths": ["Python"],
        "missing_skills": ["SQL"],
        "summary": "Line one.\nLine two.",
        "unexpected_field": "hacked"
    }
    with pytest.raises(ValidationError) as exc_info:
        MatchResult(**data_extra)
    assert "Extra inputs are not permitted" in str(exc_info.value)


def test_fallback_result():
    """Test get_fallback_result helper produces valid MatchResult."""
    fallback = get_fallback_result("Test failure reason.")
    assert fallback.match_score == 0
    assert fallback.top_strengths == ["Evaluation unavailable."]
    assert fallback.missing_skills == ["Evaluation could not be completed."]
    assert len(fallback.summary.splitlines()) == 2
    assert "Test failure reason." in fallback.summary
