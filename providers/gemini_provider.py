"""
Google Gemini provider using the official google-genai SDK.
"""

from typing import Optional

from google import genai
from google.genai import types

from config import ConfigurationError, config
from models import MatchResult
from prompts import SYSTEM_PROMPT
from providers.base import LLMProvider
from services.retry import with_retry


class GeminiProvider(LLMProvider):
    """LLM provider backed by the Google GenAI Python SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout_seconds: Optional[int] = None) -> None:
        self.api_key = api_key or config.gemini_api_key
        self.model = model or config.gemini_model
        self.timeout_seconds = timeout_seconds or config.llm_timeout_seconds

        if not self.api_key:
            raise ConfigurationError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=self.timeout_seconds * 1000),
        )

    @with_retry(max_retries=3, initial_delay=1.0)
    def evaluate(self, resume_text: str, job_description: str, repair_prompt: Optional[str] = None) -> str:
        """Evaluate resume content with Gemini structured JSON output."""
        prompt_content = f"Candidate Resume:\n{resume_text}\n\nJob Description:\n{job_description}"

        if repair_prompt:
            prompt_content += f"\n\nOutput repair instructions:\n{repair_prompt}"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0,
                response_mime_type="application/json",
                response_schema=MatchResult,
            ),
        )

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, MatchResult):
            return parsed.model_dump_json()

        response_text = getattr(response, "text", None)
        if not response_text:
            raise ValueError("Gemini returned an empty response.")
        return response_text
