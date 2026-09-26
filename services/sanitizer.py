"""
Safe JSON extraction from LLM responses.
"""

import json
import re
from typing import Any


class JSONSanitizationError(Exception):
    """Raised when a valid JSON object cannot be recovered safely."""


def sanitize_json_string(raw_text: str) -> dict[str, Any]:
    """Extract the first parseable JSON object without using executable parsing."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise JSONSanitizationError("LLM response is empty or not a string.")

    text = raw_text.strip()
    fence_match = re.search(
        r"```(?:json)?\s*([\s\S]*?)\s*```",
        text,
        flags=re.IGNORECASE,
    )
    if fence_match:
        text = fence_match.group(1).strip()

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise JSONSanitizationError("No valid JSON object could be recovered from the LLM response.")
