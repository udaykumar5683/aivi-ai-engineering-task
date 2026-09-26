"""JSON sanitizer tests."""

import pytest

from services.sanitizer import JSONSanitizationError, sanitize_json_string


def test_clean_json():
    result = sanitize_json_string(
        '{"match_score": 90, "top_strengths": ["Python"], "missing_skills": [], "summary": "Line 1\\nLine 2"}'
    )
    assert result["match_score"] == 90


def test_markdown_code_fence():
    fence = chr(96) * 3
    raw = (
        fence + "json\\n"
        + '{ "match_score": 80, "top_strengths": ["Python"], "missing_skills": ["AWS"], "summary": "First line.\\nSecond line." }'
        + "\\n" + fence
    )
    result = sanitize_json_string(raw)
    assert result["match_score"] == 80


def test_surrounding_text():
    raw = (
        "Here is the JSON: "
        + '{ "match_score": 75, "top_strengths": ["Docker"], "missing_skills": ["Kubernetes"], "summary": "Line 1.\\nLine 2." }'
        + " Done."
    )
    result = sanitize_json_string(raw)
    assert result["match_score"] == 75


def test_braces_inside_json_string():
    raw = '{ "match_score": 70, "top_strengths": ["Python {backend}"], "missing_skills": [], "summary": "Line 1\\nLine 2" }'
    result = sanitize_json_string(raw)
    assert result["top_strengths"] == ["Python {backend}"]


def test_multiple_json_candidates():
    raw = (
        "ignore {not valid} then "
        + '{ "match_score": 65, "top_strengths": ["Python"], "missing_skills": [], "summary": "Line 1\\nLine 2" }'
    )
    result = sanitize_json_string(raw)
    assert result["match_score"] == 65


def test_invalid_json_raises():
    with pytest.raises(JSONSanitizationError):
        sanitize_json_string("No JSON here.")


def test_malformed_json_raises():
    with pytest.raises(JSONSanitizationError):
        sanitize_json_string('{"match_score": 90, "top_strengths": [Python]}')
