"""
Module 9 — Risk Score Calculator.

Aggregates sub-scores from Modules 2–8 into a single weighted risk score,
assigns a risk level (Low / Medium / High), and estimates a forgery
probability capped at 85 %.
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

RiskLevel = Literal["Low", "Medium", "High"]

# ---------------------------------------------------------------------------
# Weight table — must sum to 100
# ---------------------------------------------------------------------------

_MODULE_WEIGHTS: dict[str, int] = {
    "module2_ocr":        10,
    "module3_layout":     10,
    "module4_signature":  15,
    "module5_metadata":   20,
    "module6_content":    20,
    "module7_compliance": 15,
    "module8_similarity": 10,
}

assert sum(_MODULE_WEIGHTS.values()) == 100, "Module weights must sum to 100"

# ---------------------------------------------------------------------------
# Risk-level thresholds
# ---------------------------------------------------------------------------

_LOW_CEILING = 30
_MEDIUM_CEILING = 60

# Forgery-probability scaling factor (cap at 85 %)
_FORGERY_SCALE = 0.85


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def _classify_risk(score: float) -> RiskLevel:
    """Map a 0–100 score to a human-readable risk level."""
    if score <= _LOW_CEILING:
        return "Low"
    if score <= _MEDIUM_CEILING:
        return "Medium"
    return "High"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_risk_score(module_results: dict) -> dict:
    """
    Compute an overall risk score from individual module sub-scores.

    Each entry in *module_results* is keyed by module name (e.g.
    ``"module2_ocr"``) and must contain a ``"score"`` field with an
    integer or float in the range 0–100 (0 = clean, 100 = highest risk).
    Modules that are missing or whose score is unparseable are treated
    as 0 (no additional risk).

    Args:
        module_results: Mapping of module name → result dict with at
                        least a ``"score"`` key.

    Returns:
        A dict with keys:
            overall_score       (float, 0–100)
            risk_level          ("Low" | "Medium" | "High")
            forgery_probability (float, 0.0–0.85)
            module_scores       (dict mapping module name → clamped score)
    """
    module_scores: dict[str, float] = {}
    weighted_sum: float = 0.0

    for module_name, weight in _MODULE_WEIGHTS.items():
        raw = module_results.get(module_name, {})

        # Accept either a dict with a "score" key or a bare numeric value
        if isinstance(raw, dict):
            score_value = raw.get("score", 0)
        elif isinstance(raw, (int, float)):
            score_value = raw
        else:
            score_value = 0

        try:
            score = _clamp(float(score_value))
        except (TypeError, ValueError):
            logger.warning(
                "Module 9: Non-numeric score for %s (%r); defaulting to 0.",
                module_name,
                score_value,
            )
            score = 0.0

        module_scores[module_name] = score
        weighted_sum += score * weight

    overall_score = round(weighted_sum / 100.0, 2)
    risk_level = _classify_risk(overall_score)
    forgery_probability = round(
        min(overall_score / 100.0 * _FORGERY_SCALE, _FORGERY_SCALE), 4
    )

    return {
        "overall_score": overall_score,
        "risk_level": risk_level,
        "forgery_probability": forgery_probability,
        "module_scores": module_scores,
    }
