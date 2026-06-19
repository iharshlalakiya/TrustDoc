from pathlib import Path

from fastapi import HTTPException, status

ALLOWED_EXTENSIONS = {"pptx", "pdf", "docx"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def validate_file_type(filename: str) -> str:
    """Return the lowercase file extension if allowed, else raise HTTPException."""
    extension = Path(filename).suffix.lstrip(".").lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file type '{extension or 'unknown'}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    return extension


def validate_file_size(size_bytes: int) -> None:
    """Raise HTTPException if the file exceeds the 20 MB limit."""
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 20 MB limit.",
        )
