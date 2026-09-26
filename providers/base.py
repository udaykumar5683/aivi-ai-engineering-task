"""
Abstract base class defining the provider interface for LLM evaluations.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """
    Abstract interface for LLM provider implementations (Groq, Gemini, etc.).
    Decouples evaluation logic from model vendor SDKs.
    """

    @abstractmethod
    def evaluate(
        self,
        resume_text: str,
        job_description: str,
        repair_prompt: Optional[str] = None
    ) -> str:
        """
        Send evaluation request or repair prompt to the LLM provider.

        Args:
            resume_text: Raw candidate resume content.
            job_description: Job description requirements.
            repair_prompt: Optional concise repair instructions for fixing invalid JSON.

        Returns:
            Raw response text from the LLM provider (expected to be JSON).
        """
        pass
