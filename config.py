"""
Runtime configuration for the resume-to-JD evaluation pipeline.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    """Raised when application configuration is missing or invalid."""


def _env_int(name: str, default: int, minimum: int) -> int:
    """Read and validate an integer environment variable."""
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}.") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}, got {value}.")
    return value


@dataclass(frozen=True)
class Config:
    """Application settings loaded when a Config instance is created."""

    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq").lower().strip())
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip())
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip())
    max_input_length: int = field(default_factory=lambda: _env_int("MAX_INPUT_LENGTH", 50000, 1))
    llm_timeout_seconds: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT_SECONDS", 30, 1))

    def validate(self) -> None:
        """Validate provider selection and required credentials."""
        if self.llm_provider not in {"groq", "gemini"}:
            raise ConfigurationError(
                f"Unsupported LLM_PROVIDER {self.llm_provider!r}. Use groq or gemini."
            )

        if self.llm_provider == "groq" and not self.groq_api_key:
            raise ConfigurationError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")

        if self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")


config = Config()
