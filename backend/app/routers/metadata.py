"""
Router: /metadata
Exposes POST /metadata/{document_id} which runs Module 5 (metadata analysis)
against a previously uploaded document and persists the result to
analysis_results in Supabase.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.db.supabase_client import get_supabase_client
from app.modules.module5_metadata import analyze_metadata

router = APIRouter(prefix="/metadata", tags=["metadata"])

STORAGE_BUCKET = "documents"
MODULE_NUMBER = 5
MODULE_NAME = "metadata_analysis"


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
    Download the file from Supabase Storage into a NamedTemporaryFile and
    return its path.  The caller is responsible for cleanup.
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


def _persist_result(supabase, document_id: str, report: dict) -> None:
    """Insert the module 5 result into analysis_results."""
    flags = report.get("flags", [])
    findings = {k: v for k, v in report.items() if k != "flags"}

    # Derive a numeric score from integrity label (Low=30, Medium=65, High=95)
    integrity_score = {"Low": 30, "Medium": 65, "High": 95}.get(
        report.get("metadata_integrity", "High"), 95
    )

    supabase.table("analysis_results").insert(
        {
            "document_id": document_id,
            "module_number": MODULE_NUMBER,
            "module_name": MODULE_NAME,
            "score": float(integrity_score),
            "confidence": float(report.get("confidence", 1.0)),
            "findings": findings,
            "flags": flags,
        }
    ).execute()


@router.post("/{document_id}")
async def run_metadata_analysis(document_id: str):
    """
    Run Module 5 metadata analysis on an uploaded document.

    - Fetches document record from Supabase.
    - Downloads file from Supabase Storage to a temp location.
    - Calls `analyze_metadata` and returns the full forensic report.
    - Persists the result in `analysis_results`.

    Returns the metadata forensic report on success.
    """
    supabase = get_supabase_client()

    # 1. Fetch document metadata
    doc = _fetch_document_row(supabase, document_id)
    file_type: str = doc["file_type"]

    # Module 5 only supports pptx and pdf
    if file_type not in ("pptx", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Metadata analysis supports pptx and pdf files only. "
                f"Got file_type='{file_type}'."
            ),
        )

    # 2. Download file to a temp path
    tmp_path = _download_to_temp(supabase, document_id, doc["filename"])

    try:
        # 3. Run analysis
        try:
            report = analyze_metadata(str(tmp_path), file_type)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Metadata analysis failed: {exc}",
            ) from exc

        # 4. Persist result
        try:
            _persist_result(supabase, document_id, report)
        except Exception:
            # Non-fatal: return the report even if persistence fails
            pass

    finally:
        # 5. Always clean up the temp file
        tmp_path.unlink(missing_ok=True)

    return {
        "document_id": document_id,
        "module": MODULE_NAME,
        **report,
    }
