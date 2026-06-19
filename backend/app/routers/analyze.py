"""
Router: /analyze
Orchestrates the full document forensics pipeline.

POST /analyze/{document_id}
  1. Fetch document record from Supabase
  2. Download file to a temp path
  3. Run modules in sequence: 1 → 2 → 5 → 6 → 7 → 9 → 10
  4. Persist each module result into analysis_results
  5. Insert final verdict into risk_reports
  6. Mark document status = "done"
  7. Return the complete analysis
"""

import json
import logging
import tempfile
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.db.supabase_client import get_supabase_client
from app.modules.module1_classification import classify_document
from app.modules.module2_ocr import validate_ocr
from app.modules.module_fingerprint import analyze_font_fingerprint
from app.modules.module5_metadata import analyze_metadata
from app.modules.module6_content import check_content_consistency
from app.modules.module7_compliance import review_compliance
from app.modules.module_heatmap import generate_tamper_heatmap
from app.modules.module9_risk import calculate_risk_score
from app.modules.module10_report import generate_verdict

router = APIRouter(prefix="/analyze", tags=["analyze"])
logger = logging.getLogger(__name__)

STORAGE_BUCKET = "documents"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_document_row(supabase, document_id: str) -> dict:
    """Fetch the documents row for *document_id* or raise 404."""
    import uuid
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    result = (
        supabase.table("documents")
        .select("id, filename, file_type, file_url, status")
        .eq("id", document_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return result.data



def _download_to_temp(supabase, document_id: str, filename: str) -> Path:
    """
    Download the file from Supabase Storage into a temp file and return its
    path.  The caller is responsible for cleanup.
    """
    storage_path = f"{document_id}/{filename}"
    try:
        content: bytes = supabase.storage.from_(STORAGE_BUCKET).download(storage_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download document from storage: {exc}",
        ) from exc

    suffix = Path(filename).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _persist_analysis_result(
    supabase,
    document_id: str,
    module_number: int,
    module_name: str,
    result: dict,
    *,
    error: str | None = None,
) -> None:
    """Insert one row into analysis_results for a module run."""
    score = result.get("score")
    confidence = result.get("confidence")
    flags = result.get("flags", [])

    # Build findings from everything except internal bookkeeping keys
    _EXCLUDE = {"score", "confidence", "flags", "error"}
    findings = {k: v for k, v in result.items() if k not in _EXCLUDE}
    if error:
        findings["error"] = error

    try:
        supabase.table("analysis_results").insert(
            {
                "document_id": document_id,
                "module_number": module_number,
                "module_name": module_name,
                "score": float(score) if score is not None else None,
                "confidence": float(confidence) if confidence is not None else None,
                "findings": _make_json_safe(findings),
                "flags": _make_json_safe(flags),
            }
        ).execute()
    except Exception:
        logger.exception(
            "Failed to persist analysis_results for module %s (doc %s)",
            module_name,
            document_id,
        )


def _persist_risk_report(
    supabase, document_id: str, risk: dict, verdict: dict
) -> dict:
    """Insert a row into risk_reports and return the persisted data."""
    row = {
        "document_id": document_id,
        "overall_score": int(round(risk.get("overall_score", 0))),
        "risk_level": risk.get("risk_level", "Medium"),
        "forgery_probability": float(risk.get("forgery_probability", 0)),
        "verdict": verdict.get("verdict", ""),
        "summary": verdict.get("summary", ""),
    }
    try:
        result = supabase.table("risk_reports").insert(row).execute()
        return result.data[0] if result.data else row
    except Exception:
        logger.exception(
            "Failed to persist risk_report for document %s", document_id
        )
        return row


def _update_document_status(supabase, document_id: str, new_status: str) -> None:
    """Set documents.status for the given ID."""
    try:
        supabase.table("documents").update({"status": new_status}).eq(
            "id", document_id
        ).execute()
    except Exception:
        logger.exception(
            "Failed to update document status to '%s' for %s",
            new_status,
            document_id,
        )


def _make_json_safe(obj):
    """
    Recursively convert an object so it can be serialised to JSON by Supabase.
    Handles datetime objects, sets, and other non-serialisable types.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    if isinstance(obj, set):
        return [_make_json_safe(item) for item in sorted(obj)]
    # datetime, Path, etc. → string
    return str(obj)


# ---------------------------------------------------------------------------
# Score derivation helpers
# ---------------------------------------------------------------------------

_INTEGRITY_TO_SCORE = {"Low": 85, "Medium": 50, "High": 15}
_RISK_LEVEL_TO_SCORE = {"High": 85, "Medium": 50, "Low": 15}


def _ocr_score(result: dict) -> float:
    """Derive a 0-100 risk score from module 2 OCR output."""
    if result.get("error"):
        return 50.0  # unknown → moderate risk
    anomaly_count = len(result.get("anomalies_found", []))
    # Each anomaly adds ~8 points, capped at 100
    return min(100.0, anomaly_count * 8.0)


def _fingerprint_score(result: dict) -> float:
    """Derive a 0-100 risk score from module 3 font fingerprint output."""
    if result.get("error"):
        return 50.0
    consistency = result.get("overall_consistency", "Consistent")
    font_anomalies = len(result.get("font_anomalies", []))
    spacing_anomalies = len(result.get("spacing_anomalies", []))
    
    # Base score from consistency level
    consistency_scores = {"Consistent": 10, "Mixed": 45, "Inconsistent": 75}
    base_score = consistency_scores.get(consistency, 50)
    
    # Add points for anomalies
    anomaly_score = font_anomalies * 5 + spacing_anomalies * 2
    
    return min(100.0, base_score + anomaly_score)


def _metadata_score(result: dict) -> float:
    """Derive a 0-100 risk score from module 5 metadata output."""
    return float(
        _INTEGRITY_TO_SCORE.get(result.get("metadata_integrity", "High"), 15)
    )


def _content_score(result: dict) -> float:
    """Derive a 0-100 risk score from module 6 content output."""
    if result.get("error"):
        return 50.0
    contradictions = len(result.get("contradictions", []))
    unverified = len(result.get("unverified_external_stats", []))
    return min(100.0, contradictions * 25.0 + unverified * 10.0)


def _compliance_score(result: dict) -> float:
    """Derive a 0-100 risk score from module 7 compliance output."""
    return float(
        _RISK_LEVEL_TO_SCORE.get(result.get("risk_level", "Low"), 15)
    )


# ---------------------------------------------------------------------------
# Text extraction (reuses module 1 helpers)
# ---------------------------------------------------------------------------

def _extract_text_for_llm(file_path: str, file_type: str) -> str:
    """
    Quick text extraction used to feed modules 6 and 7.
    Re-uses the extraction logic from module 1 internals.
    """
    from app.modules.module1_classification import _extract_content

    text, _count, _hidden = _extract_content(Path(file_path), file_type)
    return text


# ---------------------------------------------------------------------------
# Orchestrator endpoint
# ---------------------------------------------------------------------------


@router.post("/{document_id}")
async def analyze_document(document_id: str):
    """
    Run the full TrustDoc forensics pipeline on an uploaded document.

    Executes modules 1 → 2 → 5 → 6 → 7 → 9 → 10 in sequence, persists
    every result, produces a risk report, and returns the complete analysis.
    """
    supabase = get_supabase_client()

    # ── 1. Fetch document record ──────────────────────────────────────────
    doc = _fetch_document_row(supabase, document_id)
    file_type: str = doc["file_type"]
    filename: str = doc["filename"]

    # Mark processing
    _update_document_status(supabase, document_id, "processing")

    # ── 2. Download to temp ───────────────────────────────────────────────
    tmp_path = _download_to_temp(supabase, document_id, filename)

    try:
        all_results: dict[str, dict] = {}
        analysis_rows: list[dict] = []
        extracted_text: str = ""
        classification: dict = {}

        # ── Module 1: Classification ──────────────────────────────────────
        try:
            classification = classify_document(str(tmp_path), file_type)
            classification["score"] = 0.0  # classification itself isn't a risk
            all_results["module1_classification"] = classification
            _persist_analysis_result(
                supabase, document_id, 1, "classification", classification
            )
            analysis_rows.append({"module": "classification", **classification})
            logger.info("Module 1 (classification) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 1 failed for %s:\n%s", document_id, err)
            error_result = {"error": str(err), "score": None, "confidence": None}
            all_results["module1_classification"] = error_result
            _persist_analysis_result(
                supabase, document_id, 1, "classification", error_result, error=err
            )
            analysis_rows.append({"module": "classification", "error": err})

        # ── Module 2: OCR Validation ──────────────────────────────────────
        try:
            expected_terms = (
                classification.get("key_entities", {}).get("tech", [])
                if classification
                else []
            )
            ocr_result = validate_ocr(str(tmp_path), file_type, expected_terms)
            ocr_result["score"] = _ocr_score(ocr_result)
            all_results["module2_ocr"] = ocr_result
            _persist_analysis_result(
                supabase, document_id, 2, "ocr_validation", ocr_result
            )
            analysis_rows.append({"module": "ocr_validation", **ocr_result})
            logger.info("Module 2 (OCR) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 2 failed for %s:\n%s", document_id, err)
            error_result = {"error": str(err), "score": 50.0, "confidence": None}
            all_results["module2_ocr"] = error_result
            _persist_analysis_result(
                supabase, document_id, 2, "ocr_validation", error_result, error=err
            )
            analysis_rows.append({"module": "ocr_validation", "error": err})

        # ── Module 3: Font Fingerprint ────────────────────────────────────
        try:
            fingerprint_result = analyze_font_fingerprint(str(tmp_path), file_type)
            fingerprint_result["score"] = _fingerprint_score(fingerprint_result)
            all_results["module3_fingerprint"] = fingerprint_result
            _persist_analysis_result(
                supabase, document_id, 3, "font_fingerprint", fingerprint_result
            )
            analysis_rows.append({"module": "font_fingerprint", **fingerprint_result})
            logger.info("Module 3 (fingerprint) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 3 failed for %s:\n%s", document_id, err)
            error_result = {"error": str(err), "score": 50.0, "confidence": None}
            all_results["module3_fingerprint"] = error_result
            _persist_analysis_result(
                supabase, document_id, 3, "font_fingerprint", error_result, error=err
            )
            analysis_rows.append({"module": "font_fingerprint", "error": err})

        # ── Extract text for LLM modules ──────────────────────────────────
        try:
            extracted_text = _extract_text_for_llm(str(tmp_path), file_type)
        except Exception:
            logger.warning("Text extraction failed for %s; LLM modules will get empty text.", document_id)
            extracted_text = ""

        # ── Module 5: Metadata Analysis ───────────────────────────────────
        try:
            meta_result = analyze_metadata(str(tmp_path), file_type)
            meta_result["score"] = _metadata_score(meta_result)
            all_results["module5_metadata"] = meta_result
            _persist_analysis_result(
                supabase, document_id, 5, "metadata_analysis", meta_result
            )
            analysis_rows.append({"module": "metadata_analysis", **meta_result})
            logger.info("Module 5 (metadata) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 5 failed for %s:\n%s", document_id, err)
            error_result = {"error": str(err), "score": 50.0, "confidence": None}
            all_results["module5_metadata"] = error_result
            _persist_analysis_result(
                supabase, document_id, 5, "metadata_analysis", error_result, error=err
            )
            analysis_rows.append({"module": "metadata_analysis", "error": err})

        # ── Module 6: Content Consistency ─────────────────────────────────
        try:
            entities = classification.get("key_entities", {})
            content_result = check_content_consistency(extracted_text, entities)
            content_result["score"] = _content_score(content_result)
            all_results["module6_content"] = content_result
            _persist_analysis_result(
                supabase, document_id, 6, "content_consistency", content_result
            )
            analysis_rows.append({"module": "content_consistency", **content_result})
            logger.info("Module 6 (content) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 6 failed for %s:\n%s", document_id, err)
            error_result = {"error": str(err), "score": 50.0, "confidence": None}
            all_results["module6_content"] = error_result
            _persist_analysis_result(
                supabase, document_id, 6, "content_consistency", error_result, error=err
            )
            analysis_rows.append({"module": "content_consistency", "error": err})

        # ── Module 7: Compliance Review ───────────────────────────────────
        try:
            compliance_result = review_compliance(extracted_text)
            compliance_result["score"] = _compliance_score(compliance_result)
            all_results["module7_compliance"] = compliance_result
            _persist_analysis_result(
                supabase, document_id, 7, "compliance_review", compliance_result
            )
            analysis_rows.append({"module": "compliance_review", **compliance_result})
            logger.info("Module 7 (compliance) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 7 failed for %s:\n%s", document_id, err)
            error_result = {"error": str(err), "score": 50.0, "confidence": None}
            all_results["module7_compliance"] = error_result
            _persist_analysis_result(
                supabase, document_id, 7, "compliance_review", error_result, error=err
            )
            analysis_rows.append({"module": "compliance_review", "error": err})

        # ── Heatmap Module ────────────────────────────────────────────────
        try:
            # Gather flagged findings from all modules
            flagged_findings = {
                "document_id": document_id,
                "module2_ocr": all_results.get("module2_ocr", {}),
                "module3_fingerprint": all_results.get("module3_fingerprint", {}),
                "module5_metadata": all_results.get("module5_metadata", {}),
                "module6_content": all_results.get("module6_content", {}),
                "module7_compliance": all_results.get("module7_compliance", {}),
            }
            heatmap_result = await generate_tamper_heatmap(
                str(tmp_path), file_type, flagged_findings
            )
            heatmap_result["score"] = None
            heatmap_result["confidence"] = None
            all_results["heatmap"] = heatmap_result
            _persist_analysis_result(
                supabase, document_id, 8, "heatmap", heatmap_result
            )
            analysis_rows.append({"module": "heatmap", **heatmap_result})
            logger.info("Heatmap module complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Heatmap module failed for %s:\n%s", document_id, err)
            error_result = {"error": str(err), "score": None, "confidence": None, "pages": []}
            all_results["heatmap"] = error_result
            _persist_analysis_result(
                supabase, document_id, 8, "heatmap", error_result, error=err
            )
            analysis_rows.append({"module": "heatmap", "error": err})

        # ── Module 9: Risk Score ──────────────────────────────────────────
        try:
            risk_result = calculate_risk_score(all_results)
            risk_result["score"] = risk_result.get("overall_score", 0)
            risk_result["confidence"] = 1.0  # deterministic calculation
            all_results["module9_risk"] = risk_result
            _persist_analysis_result(
                supabase, document_id, 9, "risk_scoring", risk_result
            )
            analysis_rows.append({"module": "risk_scoring", **risk_result})
            logger.info("Module 9 (risk) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 9 failed for %s:\n%s", document_id, err)
            risk_result = {
                "overall_score": 50.0,
                "risk_level": "Medium",
                "forgery_probability": 0.425,
                "module_scores": {},
                "error": str(err),
                "score": 50.0,
                "confidence": None,
            }
            all_results["module9_risk"] = risk_result
            _persist_analysis_result(
                supabase, document_id, 9, "risk_scoring", risk_result, error=err
            )
            analysis_rows.append({"module": "risk_scoring", "error": err})

        # ── Module 10: Verdict / Report ───────────────────────────────────
        try:
            verdict_result = generate_verdict(all_results, risk_result)
            verdict_result["score"] = None  # not a numeric score
            verdict_result["confidence"] = None
            all_results["module10_report"] = verdict_result
            _persist_analysis_result(
                supabase, document_id, 10, "verdict_report", verdict_result
            )
            analysis_rows.append({"module": "verdict_report", **verdict_result})
            logger.info("Module 10 (verdict) complete for %s", document_id)
        except Exception:
            err = traceback.format_exc()
            logger.error("Module 10 failed for %s:\n%s", document_id, err)
            verdict_result = {
                "verdict": "Analysis incomplete — verdict generation failed.",
                "summary": "One or more modules encountered errors during analysis.",
                "recommended_action": "Review",
                "error": str(err),
                "score": None,
                "confidence": None,
            }
            all_results["module10_report"] = verdict_result
            _persist_analysis_result(
                supabase, document_id, 10, "verdict_report", verdict_result, error=err
            )
            analysis_rows.append({"module": "verdict_report", "error": err})

        # ── 5. Persist risk_reports row ───────────────────────────────────
        risk_report_row = _persist_risk_report(
            supabase, document_id, risk_result, verdict_result
        )

        # ── 6. Mark document as done ──────────────────────────────────────
        _update_document_status(supabase, document_id, "done")

    finally:
        # Always clean up the temp file
        tmp_path.unlink(missing_ok=True)

    # ── 7. Return full result ─────────────────────────────────────────────
    return _make_json_safe(
        {
            "document_id": document_id,
            "status": "done",
            "risk_report": risk_report_row,
            "analysis_results": analysis_rows,
        }
    )
