"""
Unit tests for repair retry flow, fallback outputs, and input validation handling.
"""

from unittest.mock import MagicMock
from models import MatchResult
from providers.base import LLMProvider
from services.evaluator import evaluate_resume, validate_inputs, InputValidationError


class MockFailingProvider(LLMProvider):
    """Mock provider that returns invalid JSON initially, then succeeds on repair."""
    def __init__(self, primary_output: str, repair_output: str):
        self.primary_output = primary_output
        self.repair_output = repair_output
        self.call_count = 0

    def evaluate(self, resume_text: str, job_description: str, repair_prompt=None) -> str:
        self.call_count += 1
        if repair_prompt:
            return self.repair_output
        return self.primary_output


class MockAlwaysFailingProvider(LLMProvider):
    """Mock provider that always returns invalid output."""
    def evaluate(self, resume_text: str, job_description: str, repair_prompt=None) -> str:
        return "Totally broken unparseable output with no JSON"


def test_one_shot_repair_success():
    """Test that evaluator attempts one repair call when primary output is invalid JSON."""
    invalid_primary = "Here is bad json: {match_score: invalid}"
    valid_repair = """{
        "match_score": 82,
        "top_strengths": ["Python"],
        "missing_skills": ["Docker"],
        "summary": "Repaired score computed successfully.\\nLine two of repaired summary."
    }"""

    provider = MockFailingProvider(invalid_primary, valid_repair)
    result = evaluate_resume("Valid Resume", "Valid JD", provider)

    assert provider.call_count == 2
    assert result.match_score == 82
    assert result.top_strengths == ["Python"]


def test_fallback_on_unrecoverable_failure():
    """Test that fallback response is returned when both primary and repair attempts fail."""
    provider = MockAlwaysFailingProvider()
    result = evaluate_resume("Valid Resume", "Valid JD", provider)

    assert isinstance(result, MatchResult)
    assert result.match_score == 0
    assert result.top_strengths == ["Evaluation unavailable."]
    assert result.missing_skills == ["Evaluation could not be completed."]
    assert "The AI evaluation could not be parsed" in result.summary


def test_empty_input_handling():
    """Test that empty inputs are rejected and return fallback response."""
    provider = MockAlwaysFailingProvider()

    # Empty resume
    res1 = evaluate_resume("", "Valid Job Description", provider)
    assert res1.match_score == 0
    assert "Input validation error" in res1.summary

    # Whitespace resume
    res2 = evaluate_resume("   \n\t ", "Valid Job Description", provider)
    assert res2.match_score == 0

    # Empty job description
    res3 = evaluate_resume("Valid Resume", "", provider)
    assert res3.match_score == 0


def test_validate_inputs_function():
    """Directly test validate_inputs function limits."""
    # Test valid
    r, j = validate_inputs("  Resume text  ", "  JD text  ")
    assert r == "Resume text"
    assert j == "JD text"

    # Test excessive length
    huge_resume = "A" * 60000
    try:
        validate_inputs(huge_resume, "JD text")
        assert False, "Should have raised InputValidationError"
    except InputValidationError as exc:
        assert "exceeds maximum allowed length" in str(exc)
