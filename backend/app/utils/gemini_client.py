"""
Shared Google Gemini API client.

Uses the current `google-genai` SDK (replaces the deprecated
`google-generativeai` package). Initialises once from GEMINI_API_KEY in .env
and exposes a single call_gemini(prompt) helper used by all modules that
require LLM inference.
"""

import os

from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Initialisation — runs once at import time
# ---------------------------------------------------------------------------

_API_KEY = os.getenv("GEMINI_API_KEY")
if not _API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set. "
        "Add it to your .env file before starting the server."
    )

_client = genai.Client(api_key=_API_KEY)

_MODEL_NAME = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


def call_gemini(prompt: str) -> str:
    """
    Send *prompt* to Gemini and return the raw text response.

    Args:
        prompt: The full prompt string to send.

    Returns:
        The model's text response as a plain string.

    Raises:
        RuntimeError: If the Gemini API call fails.
    """
    try:
        response = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,       # low temp for deterministic JSON output
                max_output_tokens=2048,
            ),
        )
        return response.text
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc
