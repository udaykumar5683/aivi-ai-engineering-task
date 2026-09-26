"""
Evaluator service orchestrating input validation, LLM invocation, JSON sanitization,
Pydantic model validation, repair retry attempt, and fallback generation.
"""

import sys
import logging
from typing import Tuple
from pydantic import ValidationError

from config import config
from models import MatchResult, get_fallback_result
from prompts import REPAIR_PROMPT_TEMPLATE
from providers.base import LLMProvider
from services.sanitizer import sanitize_json_string, JSONSanitizationError

logger = logging.getLogger(__name__)


class InputValidationError(ValueError):
    """Raised when input resume or job description text is invalid or exceeds boundaries."""
    pass


def validate_inputs(resume_text: str, job_description: str) -> Tuple[str, str]:
    """
    Validate and clean resume and job description text.

    Raises:
        InputValidationError: If either input is empty or exceeds length limits.
    """
    if not resume_text or not isinstance(resume_text, str):
        raise InputValidationError("Resume text cannot be empty or non-string.")

    if not job_description or not isinstance(job_description, str):
        raise InputValidationError("Job description text cannot be empty or non-string.")

    clean_resume = resume_text.strip()
    clean_jd = job_description.strip()

    if not clean_resume:
        raise InputValidationError("Resume text contains only whitespace.")

    if not clean_jd:
        raise InputValidationError("Job description contains only whitespace.")

    if len(clean_resume) > config.max_input_length:
        raise InputValidationError(
            f"Resume text length ({len(clean_resume)} chars) exceeds maximum allowed length of {config.max_input_length} chars."
        )

    if len(clean_jd) > config.max_input_length:
        raise InputValidationError(
            f"Job description length ({len(clean_jd)} chars) exceeds maximum allowed length of {config.max_input_length} chars."
        )

    return clean_resume, clean_jd


def evaluate_resume(
    resume_text: str,
    job_description: str,
    provider: LLMProvider
) -> MatchResult:
    """
    Evaluates a candidate resume against a job description.

    Pipeline:
    1. Validate input text (non-empty, boundary checks).
    2. Invoke LLM provider.
    3. Sanitize raw output into JSON dict.
    4. Validate dict using Pydantic MatchResult.
    5. If validation fails, attempt ONCE to repair by invoking LLM with error context.
    6. If still failing, return structured fallback MatchResult.
    """
    try:
        clean_resume, clean_jd = validate_inputs(resume_text, job_description)
    except InputValidationError as exc:
        sys.stderr.write(f"[EVALUATOR] Input validation failed: {exc}\n")
        return get_fallback_result(f"Input validation error: {exc}")

    # Primary Attempt
    raw_response = ""
    try:
        raw_response = provider.evaluate(clean_resume, clean_jd)
        sanitized_dict = sanitize_json_string(raw_response)
        match_result = MatchResult(**sanitized_dict)
        return match_result
    except (JSONSanitizationError, ValidationError, Exception) as primary_error:
        error_msg = str(primary_error)
        sys.stderr.write(f"[EVALUATOR] Primary evaluation output failed validation: {error_msg}\n")
        sys.stderr.write("[EVALUATOR] Attempting one-shot LLM output repair...\n")

        # One-shot repair attempt
        try:
            repair_instruction = REPAIR_PROMPT_TEMPLATE.format(
                error_details=error_msg,
                previous_output=raw_response[:1000] if raw_response else "No output returned"
            )
            repair_raw_response = provider.evaluate(
                resume_text=clean_resume,
                job_description=clean_jd,
                repair_prompt=repair_instruction
            )
            repair_sanitized_dict = sanitize_json_string(repair_raw_response)
            repaired_match_result = MatchResult(**repair_sanitized_dict)
            sys.stderr.write("[EVALUATOR] Output repair succeeded.\n")
            return repaired_match_result
        except Exception as repair_error:
            sys.stderr.write(f"[EVALUATOR] Repair attempt also failed: {repair_error}\n")
            return get_fallback_result("The AI evaluation could not be parsed into valid JSON structure.")
