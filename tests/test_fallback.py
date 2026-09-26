"""Tests for schema repair, fallback, and input validation."""

import pytest

from models import MatchResult
from providers.base import LLMProvider
from services.evaluator import InputValidationError, evaluate_resume, validate_inputs


class MockRepairProvider(LLMProvider):
    def __init__(self, primary_output: str, repair_output: str):
        self.primary_output = primary_output
        self.repair_output = repair_output
        self.call_count = 0

    def evaluate(self, resume_text, job_description, repair_prompt=None) -> str:
        self.call_count += 1
        return self.repair_output if repair_prompt else self.primary_output


class MockAlwaysFailingProvider(LLMProvider):
    def evaluate(self, resume_text, job_description, repair_prompt=None) -> str:
        return "Totally broken unparseable output"


class MockPermanentProvider(LLMProvider):
    def __init__(self):
        self.call_count = 0

    def evaluate(self, resume_text, job_description, repair_prompt=None) -> str:
        self.call_count += 1
        raise ValueError("Invalid API key")


def test_one_shot_repair_success():
    provider = MockRepairProvider(
        "invalid json",
        """{
            "match_score": 82,
            "top_strengths": ["Python"],
            "missing_skills": ["Docker"],
            "summary": "Repaired output is valid.\\nThe repaired result satisfies the schema."
        }""",
    )

    result = evaluate_resume("Valid Resume", "Valid JD", provider)
    assert provider.call_count == 2
    assert result.match_score == 82


def test_fallback_on_unrecoverable_schema_failure():
    provider = MockAlwaysFailingProvider()
    result = evaluate_resume("Valid Resume", "Valid JD", provider)

    assert isinstance(result, MatchResult)
    assert result.match_score == 0
    assert result.missing_skills == []
    assert "required JSON structure" in result.summary


def test_permanent_provider_failure_does_not_trigger_repair():
    provider = MockPermanentProvider()
    result = evaluate_resume("Valid Resume", "Valid JD", provider)

    assert result.match_score == 0
    assert provider.call_count == 1
    assert "provider request failed" in result.summary


def test_empty_input_handling():
    provider = MockAlwaysFailingProvider()

    result = evaluate_resume("", "Valid JD", provider)
    assert result.match_score == 0
    assert "Input validation error" in result.summary

    result = evaluate_resume("Valid Resume", "", provider)
    assert result.match_score == 0


def test_validate_inputs():
    resume, jd = validate_inputs("  Resume  ", "  JD  ")
    assert resume == "Resume"
    assert jd == "JD"

    with pytest.raises(InputValidationError):
        validate_inputs("A" * 60000, "JD")
