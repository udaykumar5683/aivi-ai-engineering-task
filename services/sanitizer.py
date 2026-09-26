"""
JSON sanitization service for extracting and parsing JSON from LLM outputs.
"""

import json
import re
from typing import Any, Dict


class JSONSanitizationError(Exception):
    """Raised when JSON output cannot be parsed or sanitized safely."""
    pass


def sanitize_json_string(raw_text: str) -> Dict[str, Any]:
    """
    Sanitize and parse raw LLM output into a Python dictionary.

    Steps:
    1. Removes markdown code block markers (e.g. ```json ... ```).
    2. Strips surrounding whitespace and conversational text.
    3. Locates the outermost JSON object boundaries '{' ... '}'.
    4. Safely parses using json.loads().

    Raises:
        JSONSanitizationError: If valid JSON cannot be located or parsed.
    """
    if not raw_text or not isinstance(raw_text, str):
        raise JSONSanitizationError("Input text for JSON sanitization is empty or not a string.")

    text = raw_text.strip()

    # Step 1: Remove markdown code fences if present
    # Matches ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match_fence = re.search(fence_pattern, text, re.IGNORECASE)
    if match_fence:
        text = match_fence.group(1).strip()

    # Step 2 & 3: Find outermost '{' and '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace > last_brace:
        raise JSONSanitizationError(
            f"No valid JSON object boundaries ('{{' and '}}') found in response: '{raw_text[:100]}...'"
        )

    json_candidate = text[first_brace:last_brace + 1].strip()

    # Step 4: Parse JSON safely without eval()
    try:
        data = json.loads(json_candidate)
        if not isinstance(data, dict):
            raise JSONSanitizationError(f"Parsed JSON is not an object/dict: type={type(data).__name__}")
        return data
    except json.JSONDecodeError as exc:
        raise JSONSanitizationError(f"Failed to parse JSON string: {exc}") from exc
