"""
Google Gemini API LLM provider implementation using the official google-genai SDK.
"""

from typing import Optional
from config import config, ConfigurationError
from prompts import SYSTEM_PROMPT
from providers.base import LLMProvider
from services.retry import with_retry

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # Handled at runtime if selected
    types = None


class GeminiProvider(LLMProvider):
    """
    LLM provider using the official Google GenAI Python SDK (google-genai).
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.gemini_api_key
        self.model = model or config.gemini_model

        if not self.api_key:
            raise ConfigurationError("GEMINI_API_KEY is not set.")

        if genai is None:
            raise ImportError(
                "The 'google-genai' package is not installed. "
                "Please run `pip install google-genai` to use GeminiProvider."
            )

        self.client = genai.Client(api_key=self.api_key)

    @with_retry(max_retries=3, initial_delay=1.0)
    def evaluate(
        self,
        resume_text: str,
        job_description: str,
        repair_prompt: Optional[str] = None
    ) -> str:
        """
        Evaluate candidate resume against job description using Gemini API.
        Enforces structured JSON output.
        """
        if repair_prompt:
            prompt_content = repair_prompt
        else:
            prompt_content = (
                f"Candidate Resume:\n{resume_text}\n\n"
                f"Job Description:\n{job_description}"
            )

        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json"
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt_content,
            config=gen_config
        )

        return response.text or ""
