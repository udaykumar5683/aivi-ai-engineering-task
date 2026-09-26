"""
Unit tests for JSON sanitization and parsing service.
"""

import pytest
from services.sanitizer import sanitize_json_string, JSONSanitizationError


def test_clean_json_parsing():
    """Test parsing clean JSON string without markdown."""
    raw = '{"match_score": 90, "top_strengths": ["Python"], "missing_skills": ["Java"], "summary": "Line 1\\nLine 2"}'
    result = sanitize_json_string(raw)
    assert isinstance(result, dict)
    assert result["match_score"] == 90


def test_markdown_code_fence_parsing():
    """Test parsing JSON enclosed in markdown code fences."""
    raw = """
```json
{
  "match_score": 80,
  "top_strengths": ["Python", "Machine Learning"],
  "missing_skills": ["AWS"],
  "summary": "First line.\\nSecond line."
}
```
"""
    result = sanitize_json_string(raw)
    assert result["match_score"] == 80
    assert len(result["top_strengths"]) == 2


def test_surrounding_conversational_text_parsing():
    """Test extracting JSON surrounded by intro and outro text."""
    raw = """
Here is the JSON output requested by your prompt:

{
  "match_score": 75,
  "top_strengths": ["Docker"],
  "missing_skills": ["Kubernetes"],
  "summary": "Line 1.\\nLine 2."
}

Hope this evaluation helps!
"""
    result = sanitize_json_string(raw)
    assert result["match_score"] == 75
    assert result["top_strengths"] == ["Docker"]


def test_invalid_json_raises_error():
    """Test invalid JSON raises JSONSanitizationError."""
    raw = "Here is some text with no JSON object at all."
    with pytest.raises(JSONSanitizationError) as exc_info:
        sanitize_json_string(raw)
    assert "No valid JSON object boundaries" in str(exc_info.value)


def test_malformed_json_syntax_raises_error():
    """Test malformed JSON syntax raises JSONSanitizationError."""
    raw = '{"match_score": 90, "top_strengths": ["Python", missing_quotes]}'
    with pytest.raises(JSONSanitizationError) as exc_info:
        sanitize_json_string(raw)
    assert "Failed to parse JSON string" in str(exc_info.value)
