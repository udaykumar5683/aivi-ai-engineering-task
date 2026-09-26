"""
Strict Pydantic v2 models for resume-to-job matching output.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator


class MatchResult(BaseModel):
    """Validated result returned by the resume-to-job evaluation pipeline."""

    model_config = ConfigDict(extra="forbid", strict=True)

    match_score: StrictInt = Field(..., ge=0, le=100, description="Compatibility score from 0 to 100.")
    top_strengths: list[StrictStr] = Field(..., min_length=1, max_length=5, description="Evidence-based strengths.")
    missing_skills: list[StrictStr] = Field(..., max_length=5, description="JD skills without sufficient resume evidence.")
    summary: StrictStr = Field(..., description="Exactly two non-empty lines.")

    @field_validator("summary")
    @classmethod
    def validate_summary_exact_two_lines(cls, value: str) -> str:
        lines = [line.strip() for line in value.strip().splitlines() if line.strip()]
        if len(lines) != 2:
            raise ValueError(f"Summary must contain exactly 2 non-empty lines, but found {len(lines)}.")
        return "\n".join(lines)

    @field_validator("top_strengths", "missing_skills")
    @classmethod
    def validate_list_items(cls, items: list[str]) -> list[str]:
        for item in items:
            if not item.strip():
                raise ValueError("List items must not be empty or whitespace.")
        return items


def get_llm_json_schema() -> dict[str, Any]:
    """Conservative provider-side schema; Pydantic performs detailed validation."""
    return {
        "type": "object",
        "properties": {
            "match_score": {"type": "integer", "description": "Compatibility score from 0 to 100."},
            "top_strengths": {"type": "array", "items": {"type": "string"}, "description": "One to five evidence-based strengths."},
            "missing_skills": {"type": "array", "items": {"type": "string"}, "description": "JD skills without sufficient resume evidence."},
            "summary": {"type": "string", "description": "Exactly two non-empty lines."},
        },
        "required": ["match_score", "top_strengths", "missing_skills", "summary"],
        "additionalProperties": False,
    }


def get_fallback_result(reason: str = "The AI evaluation could not be completed.") -> MatchResult:
    """Return a safe structured result without inventing a candidate score."""
    return MatchResult(
        match_score=0,
        top_strengths=["Evaluation unavailable."],
        missing_skills=[],
        summary=f"{reason}\nNo match score was computed.",
    )
