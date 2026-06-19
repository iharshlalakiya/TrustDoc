import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.db.supabase_client import get_supabase_client
from app.utils.file_validator import CONTENT_TYPES, validate_file_size, validate_file_type

router = APIRouter(tags=["upload"])

STORAGE_BUCKET = "documents"


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    file_type = validate_file_type(file.filename)
    content = await file.read()
    validate_file_size(len(content))

    document_id = str(uuid.uuid4())
    storage_path = f"{document_id}/{file.filename}"

    try:
        supabase = get_supabase_client()

        supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            content,
            file_options={"content-type": CONTENT_TYPES[file_type]},
        )

        file_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

        result = (
            supabase.table("documents")
            .insert(
                {
                    "id": document_id,
                    "filename": file.filename,
                    "file_url": file_url,
                    "file_type": file_type,
                    "status": "pending",
                }
            )
            .execute()
        )

        row = result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {exc}",
        ) from exc

    return {
        "document_id": row["id"],
        "filename": row["filename"],
        "file_url": row["file_url"],
        "status": row["status"],
    }
