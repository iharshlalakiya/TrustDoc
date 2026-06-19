"""
Module 10 — Verdict & Report Generator.

Sends the aggregated findings from all analysis modules together with the
risk score to Google Gemini, which returns a structured verdict comprising
a one-line ruling, an explainability summary, and a recommended action.
"""

import json
import logging
import re
from datetime import datetime, timezone

from app.utils.gemini_client import call_gemini

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """
You are a senior document-forensics analyst writing the final verdict for a
document authenticity review.  Below you are given:

1. **Module findings** — structured JSON results from seven specialised
   analysis modules (OCR quality, layout analysis, signature verification,
   metadata inspection, content-consistency check, compliance review, and
   similarity search).
2. **Risk assessment** — an overall risk score (0–100), risk level, and
   forgery probability produced by a weighted aggregation of the module
   scores.

Using ALL of this evidence, produce a JSON object with EXACTLY these three
fields — no markdown fences, no commentary before or after, just raw JSON:

{{
  "verdict": "<A single concise sentence summarising authenticity, e.g. 'Authentic, programmatically generated document' or 'Likely forged — multiple metadata and layout anomalies detected'>",
  "summary": "<A 3–5 sentence explainability paragraph. Reference specific module findings that most influenced the verdict. Mention the overall risk score and probability.>",
  "recommended_action": "<Exactly one of: Accept | Review | Reject>"
}}

Guidelines for recommended_action:
- **Accept** — risk level is Low and no significant anomalies.
- **Review** — risk level is Medium OR isolated anomalies exist.
- **Reject** — risk level is High OR multiple strong forgery indicators.

MODULE FINDINGS:
\"\"\"
{module_findings_json}
\"\"\"

RISK ASSESSMENT:
\"\"\"
{risk_result_json}
\"\"\"
""".strip()

# ---------------------------------------------------------------------------
# Fallback result
# ---------------------------------------------------------------------------

_FALLBACK: dict = {
    "verdict": "Unable to determine — analysis could not be completed.",
    "summary": (
        "The automated analysis pipeline encountered an error and was unable "
        "to produce a reliable verdict. Manual review of the document is "
        "strongly recommended."
    ),
    "recommended_action": "Review",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ACTIONS: set[str] = {"Accept", "Review", "Reject"}


def _parse_json_response(raw: str) -> dict:
    """
    Extract and parse the JSON object from a Gemini response string.

    Strips markdown code fences that Gemini sometimes prepends/appends.
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    logger.warning("Module 10: Could not parse Gemini JSON response; returning fallback.")
    return _FALLBACK


def _validate_result(data: dict) -> dict:
    """Ensure all required keys are present with reasonable defaults."""
    verdict = str(data.get("verdict", _FALLBACK["verdict"])).strip()
    summary = str(data.get("summary", _FALLBACK["summary"])).strip()

    action_raw = str(data.get("recommended_action", "Review")).strip()
    # Normalise to title-case and validate
    action = action_raw.capitalize()
    if action not in _VALID_ACTIONS:
        action = "Review"

    return {
        "verdict": verdict,
        "summary": summary,
        "recommended_action": action,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_verdict(all_module_results: dict, risk_result: dict) -> dict:
    """
    Generate a final verdict report by calling Gemini with the full
    set of module findings and the aggregated risk assessment.

    Args:
        all_module_results: Combined dict of all module outputs keyed by
                            module name (e.g. ``"module2_ocr": {...}``).
        risk_result:        Output of
                            :func:`module9_risk.calculate_risk_score`.

    Returns:
        A dict with keys:
            verdict             (str)  — one-line authenticity ruling
            summary             (str)  — 3–5 sentence explanation
            recommended_action  (str)  — "Accept" | "Review" | "Reject"
            generated_at        (str)  — ISO-8601 UTC timestamp
            error               (str)  — present if generation failed
    """
    module_findings_json = json.dumps(all_module_results, indent=2, ensure_ascii=False, default=str)
    risk_result_json = json.dumps(risk_result, indent=2, ensure_ascii=False, default=str)

    prompt = _PROMPT_TEMPLATE.format(
        module_findings_json=module_findings_json,
        risk_result_json=risk_result_json,
    )

    try:
        raw_response = call_gemini(prompt)
        logger.info("Module 10: Received Gemini response (length=%d)", len(raw_response))
        
        parsed = _parse_json_response(raw_response)
        
        # Check if parsing returned fallback
        if parsed == _FALLBACK:
            logger.error("Module 10: JSON parsing failed. Raw response: %s", raw_response[:500])
            return {
                **_FALLBACK,
                "error": "Failed to parse Gemini response",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        
        result = _validate_result(parsed)
        
    except RuntimeError as exc:
        logger.error("Module 10: Gemini call failed with RuntimeError: %s", exc, exc_info=True)
        return {
            **_FALLBACK,
            "error": f"Gemini API error: {str(exc)}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Module 10: Unexpected error: %s", exc, exc_info=True)
        return {
            **_FALLBACK,
            "error": f"Unexpected error: {str(exc)}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result
