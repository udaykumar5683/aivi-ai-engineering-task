"""
Command-line entrypoint for the resume-to-job evaluation pipeline.
"""

import argparse
import os
import sys
from pathlib import Path

from config import Config, ConfigurationError
from providers.gemini_provider import GeminiProvider
from providers.groq_provider import GroqProvider
from services.evaluator import evaluate_resume


def main() -> int:
    """Parse CLI arguments, configure the provider, and print validated JSON."""
    parser = argparse.ArgumentParser(
        description="Evaluate a raw resume against a Job Description using structured LLM output."
    )
    parser.add_argument(
        "resume_path",
        help="Path to the raw resume text file.",
    )
    parser.add_argument(
        "job_description_path",
        help="Path to the Job Description text file.",
    )
    parser.add_argument(
        "--provider",
        choices=("groq", "gemini"),
        default=None,
        help="Override LLM_PROVIDER for this run.",
    )
    args = parser.parse_args()

    provider_name = (
        args.provider
        or os.getenv("LLM_PROVIDER", "groq")
    ).lower().strip()

    try:
        current_config = Config(llm_provider=provider_name)
        current_config.validate()
    except ConfigurationError as error:
        sys.stderr.write(f"Configuration Error: {error}\n")
        return 1

    resume_file = Path(args.resume_path)
    jd_file = Path(args.job_description_path)

    if not resume_file.is_file():
        sys.stderr.write(f"Error: resume file not found: {resume_file}\n")
        return 1

    if not jd_file.is_file():
        sys.stderr.write(f"Error: Job Description file not found: {jd_file}\n")
        return 1

    try:
        resume_text = resume_file.read_text(encoding="utf-8")
        job_description_text = jd_file.read_text(encoding="utf-8")
    except OSError as error:
        sys.stderr.write(f"Error reading input files: {error}\n")
        return 1

    try:
        if provider_name == "groq":
            provider = GroqProvider(
                api_key=current_config.groq_api_key,
                model=current_config.groq_model,
                timeout_seconds=current_config.llm_timeout_seconds,
            )
        else:
            provider = GeminiProvider(
                api_key=current_config.gemini_api_key,
                model=current_config.gemini_model,
                timeout_seconds=current_config.llm_timeout_seconds,
            )
    except Exception as error:
        sys.stderr.write(
            f"Provider initialization error: {type(error).__name__}: {error}\n"
        )
        return 1

    match_result = evaluate_resume(
        resume_text,
        job_description_text,
        provider,
    )

    print(match_result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
