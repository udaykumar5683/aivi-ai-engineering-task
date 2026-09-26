"""
Configuration management for the resume-to-JD evaluation pipeline.
Handles environment variables, default model settings, and provider validation.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()


class ConfigurationError(Exception):
    """Raised when application configuration or credentials are missing or invalid."""
    pass


@dataclass(frozen=True)
class Config:
    """Application configuration settings."""
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq").lower().strip()

    # Groq settings
    groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

    # Gemini settings
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    # Input constraints
    max_input_length: int = int(os.getenv("MAX_INPUT_LENGTH", "50000"))

    def validate(self) -> None:
        """
        Validate that the selected provider has the required configuration.
        Raises ConfigurationError if invalid.
        """
        if self.llm_provider not in ("groq", "gemini"):
            raise ConfigurationError(
                f"Unsupported LLM_PROVIDER '{self.llm_provider}'. Must be 'groq' or 'gemini'."
            )

        if self.llm_provider == "groq" and not self.groq_api_key:
            raise ConfigurationError(
                "GROQ_API_KEY environment variable is missing or empty. "
                "Please set GROQ_API_KEY in your .env file or environment."
            )

        if self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY environment variable is missing or empty. "
                "Please set GEMINI_API_KEY in your .env file or environment."
            )


# Global default configuration instance
config = Config()
