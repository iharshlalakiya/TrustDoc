"""
Router: /report
Fetches the final risk report and all analysis results for a document.

GET /report/{document_id}
  Returns the risk_reports row joined with all analysis_results rows for the
  given document.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/report", tags=["report"])
logger = logging.getLogger(__name__)


@router.get("/{document_id}")
async def get_report(document_id: str):
    """
    Retrieve the full forensics report for a previously analysed document.

    Returns:
        - document: basic document metadata (id, filename, status, …)
        - risk_report: the risk_reports row (overall_score, verdict, …)
        - analysis_results: list of analysis_results rows ordered by module_number
    """
    import uuid
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    # ── Fetch document row ────────────────────────────────────────────────
    supabase = get_supabase_client()
    try:
        doc_result = (
            supabase.table("documents")
            .select("id, filename, file_type, file_url, status, uploaded_at")
            .eq("id", document_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )



    document = doc_result.data

    # ── Fetch risk report ─────────────────────────────────────────────────
    risk_result = (
        supabase.table("risk_reports")
        .select("*")
        .eq("document_id", document_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    risk_report = risk_result.data[0] if risk_result.data else None

    if risk_report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No risk report found for document '{document_id}'. "
                "Has the analysis been run?"
            ),
        )

    # ── Fetch all analysis results ────────────────────────────────────────
    analysis_result = (
        supabase.table("analysis_results")
        .select("*")
        .eq("document_id", document_id)
        .order("module_number")
        .execute()
    )
    analysis_results = analysis_result.data or []

    return {
        "document": document,
        "risk_report": risk_report,
        "analysis_results": analysis_results,
    }
