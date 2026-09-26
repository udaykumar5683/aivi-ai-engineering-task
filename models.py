"""
Pydantic v2 schemas and validation models for resume matching output.
"""

from typing import List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class MatchResult(BaseModel):
    """
    Structured model representing the resume-to-job description match evaluation.
    Enforces strict typing and semantic constraints.
    """
    model_config = ConfigDict(extra="forbid")

    match_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Compatibility score between candidate resume and job description (0 to 100)."
    )
    top_strengths: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1 to 5 key strengths supported by evidence in the resume."
    )
    missing_skills: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1 to 5 required or preferred skills missing from the resume."
    )
    summary: str = Field(
        ...,
        description="High-level evaluation summary containing exactly 2 non-empty lines."
    )

    @field_validator("summary")
    @classmethod
    def validate_summary_exact_two_lines(cls, v: str) -> str:
        """Ensure the summary consists of exactly two non-empty lines."""
        if not v or not isinstance(v, str):
            raise ValueError("Summary must be a non-empty string.")

        lines = [line.strip() for line in v.strip().splitlines() if line.strip()]
        if len(lines) != 2:
            raise ValueError(
                f"Summary must contain exactly 2 non-empty lines, but found {len(lines)}."
            )
        return "\n".join(lines)

    @field_validator("top_strengths", "missing_skills")
    @classmethod
    def validate_non_empty_items(cls, items: List[str]) -> List[str]:
        """Ensure list items are non-empty strings and within length limits."""
        cleaned = [item.strip() for item in items if isinstance(item, str) and item.strip()]
        if not (1 <= len(cleaned) <= 5):
            raise ValueError(
                f"List must contain between 1 and 5 non-empty items, got {len(cleaned)}."
            )
        return cleaned


def get_fallback_result(reason: str = "The AI evaluation could not be completed.") -> MatchResult:
    """
    Generates a safe, predictable fallback MatchResult when evaluation fails completely.
    Does not fake a candidate score during service failure.
    """
    return MatchResult(
        match_score=0,
        top_strengths=["Evaluation unavailable."],
        missing_skills=["Evaluation could not be completed."],
        summary=f"{reason}\nNo match score was computed."
    )
