"""
Evaluation orchestration for the resume-to-JD pipeline.
"""

import sys
from typing import Tuple

from pydantic import ValidationError

from config import config
from models import MatchResult, get_fallback_result
from prompts import REPAIR_PROMPT_TEMPLATE
from providers.base import LLMProvider
from services.sanitizer import JSONSanitizationError, sanitize_json_string


class InputValidationError(ValueError):
    """Raised when a resume or JD input is invalid."""


def validate_inputs(resume_text: str, job_description: str) -> Tuple[str, str]:
    """Validate required text inputs and enforce size limits."""
    if not isinstance(resume_text, str) or not resume_text.strip():
        raise InputValidationError("Resume text cannot be empty.")
    if not isinstance(job_description, str) or not job_description.strip():
        raise InputValidationError("Job description cannot be empty.")

    clean_resume = resume_text.strip()
    clean_jd = job_description.strip()

    if len(clean_resume) > config.max_input_length:
        raise InputValidationError(
            f"Resume text exceeds the maximum length of {config.max_input_length} characters."
        )
    if len(clean_jd) > config.max_input_length:
        raise InputValidationError(
            f"Job description exceeds the maximum length of {config.max_input_length} characters."
        )

    return clean_resume, clean_jd


def _log_provider_failure(stage: str, error: Exception) -> None:
    """Log provider failure metadata without dumping user documents."""
    sys.stderr.write(
        f"[EVALUATOR] {stage} provider call failed: {type(error).__name__}: {error}\n"
    )


def evaluate_resume(resume_text: str, job_description: str, provider: LLMProvider) -> MatchResult:
    """Run evaluation, one-shot schema repair, and safe fallback handling."""
    try:
        clean_resume, clean_jd = validate_inputs(resume_text, job_description)
    except InputValidationError as error:
        sys.stderr.write(f"[EVALUATOR] Input validation failed: {error}\n")
        return get_fallback_result(f"Input validation error: {error}")

    try:
        raw_response = provider.evaluate(clean_resume, clean_jd)
    except Exception as provider_error:
        _log_provider_failure("Primary", provider_error)
        return get_fallback_result("The AI provider request failed after retry attempts.")

    try:
        result_data = sanitize_json_string(raw_response)
        return MatchResult.model_validate(result_data)
    except (JSONSanitizationError, ValidationError, ValueError) as schema_error:
        sys.stderr.write(
            f"[EVALUATOR] Model output validation failed: {type(schema_error).__name__}: {schema_error}\n"
        )

    repair_prompt = REPAIR_PROMPT_TEMPLATE.format(
        error_details="The previous output failed JSON or Pydantic validation.",
        previous_output=raw_response[:2000],
    )

    try:
        repaired_raw_response = provider.evaluate(
            resume_text=clean_resume,
            job_description=clean_jd,
            repair_prompt=repair_prompt,
        )
    except Exception as repair_provider_error:
        _log_provider_failure("Repair", repair_provider_error)
        return get_fallback_result("The AI provider could not complete the structured output repair.")

    try:
        repaired_data = sanitize_json_string(repaired_raw_response)
        return MatchResult.model_validate(repaired_data)
    except (JSONSanitizationError, ValidationError, ValueError) as repair_error:
        sys.stderr.write(
            f"[EVALUATOR] Repair validation failed: {type(repair_error).__name__}: {repair_error}\n"
        )
        return get_fallback_result(
            "The AI evaluation could not be parsed into the required JSON structure."
        )
