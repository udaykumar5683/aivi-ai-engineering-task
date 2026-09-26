"""
Groq provider using strict Structured Outputs.
"""

from typing import Optional

from groq import Groq

from config import ConfigurationError, config
from models import get_llm_json_schema
from prompts import SYSTEM_PROMPT
from providers.base import LLMProvider
from services.retry import with_retry


class GroqProvider(LLMProvider):
    """LLM provider backed by the Groq Python SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout_seconds: Optional[int] = None) -> None:
        self.api_key = api_key or config.groq_api_key
        self.model = model or config.groq_model
        self.timeout_seconds = timeout_seconds or config.llm_timeout_seconds

        if not self.api_key:
            raise ConfigurationError("GROQ_API_KEY is not set.")

        self.client = Groq(api_key=self.api_key, timeout=self.timeout_seconds)

    @with_retry(max_retries=3, initial_delay=1.0)
    def evaluate(self, resume_text: str, job_description: str, repair_prompt: Optional[str] = None) -> str:
        """Evaluate resume content with provider-side strict JSON Schema output."""
        user_content = f"Candidate Resume:\n{resume_text}\n\nJob Description:\n{job_description}"

        if repair_prompt:
            user_content += f"\n\nOutput repair instructions:\n{repair_prompt}"

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "resume_job_match",
                    "strict": True,
                    "schema": get_llm_json_schema(),
                },
            },
        )

        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty response.")
        return content
