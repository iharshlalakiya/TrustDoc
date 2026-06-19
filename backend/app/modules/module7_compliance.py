"""
Module 7 — Compliance & Risk Reviewer.

Uses Google Gemini to audit a document for regulatory, legal, and ethical
compliance issues including ISO self-certification, ToS violations, PII
exposure, and GDPR/DPDPA data-protection flags.
"""

import json
import logging
import re
from typing import Literal

from app.utils.gemini_client import call_gemini

logger = logging.getLogger(__name__)

RiskLevel = Literal["Low", "Medium", "High"]

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """
You are a compliance and legal-risk auditor specialising in document forensics.

Carefully read the document text below and assess it for the following risk
categories:

1. **ISO / Certification Claims**
   — Does the document claim an ISO or other third-party certification
     (e.g. ISO 27001, ISO 9001, SOC 2) without citing a certificate number,
     issuing body, or audit date? Flag each uncorroborated claim.

2. **Terms-of-Service Violations**
   — Does the document describe, advertise, or rely on use of AI services
     (e.g. ChatGPT, GPT-4, OpenAI APIs, Claude) in ways that violate their
     ToS? Examples: representing AI-generated content as human-authored,
     using AI for deceptive, misleading, or impersonation tasks.

3. **PII Detection**
   — Identify any Personally Identifiable Information: full names paired with
     contact details, email addresses, phone numbers, Aadhaar numbers
     (12-digit Indian UID), passport numbers, financial account numbers.

4. **GDPR / DPDPA Flags**
   — Does the document collect, process, or transfer personal data without
     mentioning consent, data-retention policy, or right-to-erasure?
   — Does it reference Indian residents' data without DPDPA (Digital Personal
     Data Protection Act 2023) compliance language?

5. **Legal Admissibility Claims**
   — Does the document make claims about its own legal admissibility, court
     validity, or evidentiary weight that appear unsupported or exaggerated?

Return your analysis as a single valid JSON object — no markdown fences,
no commentary before or after, just raw JSON — with exactly this structure:

{{
  "compliance_flags": [
    {{
      "category": "<one of: ISO_CLAIM | TOS_VIOLATION | PII | GDPR_DPDPA | LEGAL_ADMISSIBILITY>",
      "severity": "<Low | Medium | High>",
      "finding": "<concise description of the issue>",
      "excerpt": "<exact or paraphrased text from the document that triggered this flag>"
    }}
  ],
  "pii_detected": <true | false>,
  "risk_level": "<Low | Medium | High>",
  "observations": [
    "<free-text observation about overall compliance posture>"
  ]
}}

Rules for risk_level:
- "High"   — any High-severity flag OR more than 2 Medium flags OR PII detected
- "Medium" — 1–2 Medium flags with no PII
- "Low"    — only Low-severity flags or no flags at all

DOCUMENT TEXT:
\"\"\"
{extracted_text}
\"\"\"
""".strip()

# ---------------------------------------------------------------------------
# Fallback result
# ---------------------------------------------------------------------------

_FALLBACK: dict = {
    "compliance_flags": [],
    "pii_detected": False,
    "risk_level": "Low",
    "observations": [],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_RISK_LEVELS: set[str] = {"Low", "Medium", "High"}


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

    logger.warning("Module 7: Could not parse Gemini JSON response; returning fallback.")
    return _FALLBACK


def _validate_result(data: dict) -> dict:
    """Ensure all required keys are present and have the correct types."""
    flags = list(data.get("compliance_flags", []))
    pii = bool(data.get("pii_detected", False))

    # Normalise risk level
    risk_raw = str(data.get("risk_level", "Low")).strip()
    risk_level: RiskLevel = risk_raw if risk_raw in _VALID_RISK_LEVELS else "Low"  # type: ignore[assignment]

    # Auto-elevate risk if PII was found and level is "Low"
    if pii and risk_level == "Low":
        risk_level = "Medium"

    return {
        "compliance_flags": flags,
        "pii_detected": pii,
        "risk_level": risk_level,
        "observations": list(data.get("observations", [])),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def review_compliance(extracted_text: str) -> dict:
    """
    Audit a document for compliance and legal-risk issues using Gemini.

    Checks for:
    - ISO/certification self-claims without proof
    - OpenAI/GPT ToS violations
    - PII (names, emails, phones, Aadhaar)
    - GDPR / DPDPA exposure
    - Unsupported legal admissibility claims

    Args:
        extracted_text: Full plain text extracted from the document.

    Returns:
        A dict with keys:
            compliance_flags  (list[dict])
            pii_detected      (bool)
            risk_level        ("Low" | "Medium" | "High")
            observations      (list[str])
    """
    if not extracted_text or not extracted_text.strip():
        logger.warning("Module 7: Empty extracted_text received; skipping Gemini call.")
        return _FALLBACK

    # Truncate to ~12 000 chars to stay within free-tier token limits
    text_snippet = extracted_text[:12_000]
    if len(extracted_text) > 12_000:
        text_snippet += "\n... [document truncated for compliance review]"

    prompt = _PROMPT_TEMPLATE.format(extracted_text=text_snippet)

    try:
        raw_response = call_gemini(prompt)
        parsed = _parse_json_response(raw_response)
        return _validate_result(parsed)
    except RuntimeError as exc:
        logger.error("Module 7: Gemini call failed — %s", exc)
        return {**_FALLBACK, "error": str(exc)}
