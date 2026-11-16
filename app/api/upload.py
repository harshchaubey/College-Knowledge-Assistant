import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.schemas.models import UploadResponse
from app.services.chunker import chunk_documents
from app.services.pdf_loader import load_pdf
from app.services.vectorstore import add_documents, delete_document

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is larger than the {settings.max_upload_mb} MB limit.",
        )

    filename = Path(file.filename).name

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / filename
        temp_path.write_bytes(content)

        try:
            pages = load_pdf(temp_path)
        except Exception as exc:
            logger.warning("Could not read %s: %s", filename, exc)
            raise HTTPException(
                status_code=400,
                detail="Could not read this PDF. It may be corrupted or password-protected.",
            ) from exc

        if not pages or all(not page.page_content.strip() for page in pages):
            raise HTTPException(
                status_code=400,
                detail="No extractable text found. Is this a scanned/image-only PDF?",
            )

        try:
            chunks = chunk_documents(pages)
            replaced = delete_document(filename) > 0
            added = add_documents(chunks)
        except Exception as exc:
            logger.exception("Indexing failed for %s", filename)
            raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}") from exc

        shutil.move(temp_path, settings.upload_dir / filename)

    return UploadResponse(
        message="PDF re-indexed." if replaced else "PDF ingested successfully.",
        filename=filename,
        pages=len(pages),
        chunks=added,
        replaced=replaced,
    )
