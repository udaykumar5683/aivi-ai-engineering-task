"""
Groq API LLM provider implementation.
"""

from typing import Optional
from config import config, ConfigurationError
from prompts import SYSTEM_PROMPT
from providers.base import LLMProvider
from services.retry import with_retry

try:
    from groq import Groq
except ImportError:
    Groq = None  # Handled at runtime instantiation if selected


class GroqProvider(LLMProvider):
    """
    LLM provider using the Groq Python SDK.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.groq_api_key
        self.model = model or config.groq_model

        if not self.api_key:
            raise ConfigurationError("GROQ_API_KEY is not set.")

        if Groq is None:
            raise ImportError(
                "The 'groq' package is not installed. "
                "Please run `pip install groq` to use GroqProvider."
            )

        self.client = Groq(api_key=self.api_key)

    @with_retry(max_retries=3, initial_delay=1.0)
    def evaluate(
        self,
        resume_text: str,
        job_description: str,
        repair_prompt: Optional[str] = None
    ) -> str:
        """
        Evaluate candidate resume against job description using Groq LLM API.
        Enforces structured JSON response format.
        """
        if repair_prompt:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": repair_prompt}
            ]
        else:
            user_content = (
                f"Candidate Resume:\n{resume_text}\n\n"
                f"Job Description:\n{job_description}"
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ]

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        content = completion.choices[0].message.content
        return content or ""
