"""
Module 6 — Content Consistency Checker.

Uses Google Gemini to identify all quantitative claims in a document,
verify their internal consistency across sections, and flag contradictions
or unverified external statistics.
"""

import json
import logging
import re

from app.utils.gemini_client import call_gemini

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """
You are a document forensics analyst specialising in factual consistency.

Analyse the document text below and perform the following tasks:

1. Identify EVERY quantitative claim in the document (numbers, percentages,
   financial figures, dates, counts, growth rates, market sizes, etc.).
2. Check whether those claims are INTERNALLY CONSISTENT across all sections.
   Flag any contradictions where the same metric appears with different values.
3. Identify any statistics that appear to reference EXTERNAL sources
   (e.g. "industry average", "according to Gartner", "market research shows")
   but have no citation — these are "unverified external stats".

Return your analysis as a single valid JSON object — no markdown fences,
no commentary before or after, just raw JSON — with exactly this structure:

{{
  "claims_consistent": <true | false>,
  "confidence": <float between 0.0 and 1.0>,
  "verified_claims": [
    {{
      "claim": "<exact text of claim>",
      "value": "<numeric value or range>",
      "section": "<section or context where it appears>",
      "consistent": <true | false>
    }}
  ],
  "contradictions": [
    {{
      "claim": "<what the contradiction is about>",
      "occurrences": ["<first instance>", "<second instance>"],
      "explanation": "<why this is a contradiction>"
    }}
  ],
  "unverified_external_stats": [
    {{
      "claim": "<exact text>",
      "missing": "<what citation or proof is missing>"
    }}
  ]
}}

DOCUMENT TEXT:
\"\"\"
{extracted_text}
\"\"\"

EXTRACTED ENTITIES (for additional context):
{entities_json}
""".strip()

# ---------------------------------------------------------------------------
# Fallback result used when JSON parsing fails
# ---------------------------------------------------------------------------

_FALLBACK: dict = {
    "claims_consistent": False,
    "confidence": 0.0,
    "verified_claims": [],
    "contradictions": [],
    "unverified_external_stats": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json_response(raw: str) -> dict:
    """
    Extract and parse the JSON object from a Gemini response string.

    Gemini occasionally wraps JSON in markdown code fences — strip them first.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract the first {...} block as a last resort
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    logger.warning("Module 6: Could not parse Gemini JSON response; returning fallback.")
    return _FALLBACK


def _validate_result(data: dict) -> dict:
    """Ensure all required keys are present with correct types."""
    return {
        "claims_consistent": bool(data.get("claims_consistent", False)),
        "confidence": float(data.get("confidence", 0.0)),
        "verified_claims": list(data.get("verified_claims", [])),
        "contradictions": list(data.get("contradictions", [])),
        "unverified_external_stats": list(data.get("unverified_external_stats", [])),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_content_consistency(extracted_text: str, entities: dict) -> dict:
    """
    Check internal quantitative consistency of a document using Gemini.

    Args:
        extracted_text: Full plain text extracted from the document.
        entities:       Key-entity dict produced by Module 1 classification
                        (team, tech, data, infra lists).

    Returns:
        A dict with keys:
            claims_consistent       (bool)
            confidence              (float 0-1)
            verified_claims         (list[dict])
            contradictions          (list[dict])
            unverified_external_stats (list[dict])
    """
    if not extracted_text or not extracted_text.strip():
        logger.warning("Module 6: Empty extracted_text received; skipping Gemini call.")
        return _FALLBACK

    # Truncate to ~12 000 chars to stay well within free-tier token limits
    text_snippet = extracted_text[:12_000]
    if len(extracted_text) > 12_000:
        text_snippet += "\n... [document truncated for analysis]"

    entities_json = json.dumps(entities, indent=2, ensure_ascii=False)

    prompt = _PROMPT_TEMPLATE.format(
        extracted_text=text_snippet,
        entities_json=entities_json,
    )

    try:
        raw_response = call_gemini(prompt)
        parsed = _parse_json_response(raw_response)
        return _validate_result(parsed)
    except RuntimeError as exc:
        logger.error("Module 6: Gemini call failed — %s", exc)
        return {**_FALLBACK, "error": str(exc)}
