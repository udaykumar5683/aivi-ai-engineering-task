"""
Command-line Interface (CLI) entrypoint for the resume evaluation pipeline.

Usage:
    python main.py samples/resume.txt samples/job_description.txt
    python main.py samples/resume.txt samples/job_description.txt --provider gemini
"""

import sys
import os
import argparse
from pathlib import Path

from config import Config, ConfigurationError
from providers.groq_provider import GroqProvider
from providers.gemini_provider import GeminiProvider
from services.evaluator import evaluate_resume


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate raw resume against a Job Description using structured LLM outputs."
    )
    parser.add_argument("resume_path", help="Path to raw resume text file.")
    parser.add_argument("job_description_path", help="Path to Job Description text file.")
    parser.add_argument(
        "--provider",
        choices=["groq", "gemini"],
        default=None,
        help="Override LLM provider configured in environment (groq or gemini)."
    )

    args = parser.parse_args()

    # Load configuration
    provider_name = (args.provider or os.getenv("LLM_PROVIDER", "groq")).lower().strip()

    # Instantiate config with selected provider override if specified
    current_config = Config(llm_provider=provider_name)

    try:
        current_config.validate()
    except ConfigurationError as cfg_err:
        sys.stderr.write(f"Configuration Error: {cfg_err}\n")
        return 1

    # Load file contents
    resume_file = Path(args.resume_path)
    jd_file = Path(args.job_description_path)

    if not resume_file.is_file():
        sys.stderr.write(f"Error: Resume file not found at '{args.resume_path}'.\n")
        return 1

    if not jd_file.is_file():
        sys.stderr.write(f"Error: Job description file not found at '{args.job_description_path}'.\n")
        return 1

    try:
        resume_text = resume_file.read_text(encoding="utf-8")
        job_description_text = jd_file.read_text(encoding="utf-8")
    except Exception as file_err:
        sys.stderr.write(f"Error reading input files: {file_err}\n")
        return 1

    # Instantiate selected provider
    try:
        if provider_name == "groq":
            provider = GroqProvider(api_key=current_config.groq_api_key, model=current_config.groq_model)
        elif provider_name == "gemini":
            provider = GeminiProvider(api_key=current_config.gemini_api_key, model=current_config.gemini_model)
        else:
            sys.stderr.write(f"Error: Unsupported provider '{provider_name}'.\n")
            return 1
    except Exception as init_err:
        sys.stderr.write(f"Provider Initialization Error: {init_err}\n")
        return 1

    # Run evaluation pipeline
    match_result = evaluate_resume(resume_text, job_description_text, provider)

    # Print ONLY the valid JSON result to stdout
    print(match_result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
