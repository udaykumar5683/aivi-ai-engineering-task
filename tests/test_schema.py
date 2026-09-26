"""Pydantic schema validation tests."""

import pytest
from pydantic import ValidationError

from models import MatchResult, get_fallback_result


def valid_data():
    return {
        "match_score": 85,
        "top_strengths": ["Python expertise", "Generative AI experience"],
        "missing_skills": ["Kubernetes"],
        "summary": "Strong alignment with the core requirements.\nKubernetes experience is not documented.",
    }


def test_valid_match_result():
    result = MatchResult(**valid_data())
    assert result.match_score == 85
    assert len(result.top_strengths) == 2
    assert len(result.summary.splitlines()) == 2


def test_empty_missing_skills_is_valid():
    data = valid_data()
    data["missing_skills"] = []
    result = MatchResult(**data)
    assert result.missing_skills == []


@pytest.mark.parametrize("score", [-1, 101])
def test_match_score_out_of_range(score):
    data = valid_data()
    data["match_score"] = score
    with pytest.raises(ValidationError):
        MatchResult(**data)


def test_invalid_summary_line_count():
    data = valid_data()
    data["summary"] = "Only one line."
    with pytest.raises(ValidationError):
        MatchResult(**data)

    data["summary"] = "First.\nSecond.\nThird."
    with pytest.raises(ValidationError):
        MatchResult(**data)


def test_list_boundaries():
    data = valid_data()
    data["top_strengths"] = []
    with pytest.raises(ValidationError):
        MatchResult(**data)

    data["top_strengths"] = ["1", "2", "3", "4", "5", "6"]
    with pytest.raises(ValidationError):
        MatchResult(**data)

    data = valid_data()
    data["missing_skills"] = ["1", "2", "3", "4", "5", "6"]
    with pytest.raises(ValidationError):
        MatchResult(**data)


def test_blank_list_item_rejected():
    data = valid_data()
    data["top_strengths"] = ["Python", "   "]
    with pytest.raises(ValidationError):
        MatchResult(**data)


def test_extra_fields_rejected():
    data = valid_data()
    data["unexpected_field"] = "hacked"
    with pytest.raises(ValidationError):
        MatchResult(**data)


def test_strict_types_rejected():
    data = valid_data()
    data["match_score"] = "85"
    with pytest.raises(ValidationError):
        MatchResult(**data)


def test_fallback_is_valid():
    fallback = get_fallback_result("Test failure reason.")
    assert fallback.match_score == 0
    assert fallback.missing_skills == []
    assert len(fallback.summary.splitlines()) == 2
