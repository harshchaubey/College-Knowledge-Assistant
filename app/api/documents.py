from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from app.config import get_settings
from app.schemas.models import DocumentInfo
from app.services.vectorstore import delete_document, list_documents

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[DocumentInfo])
def get_documents() -> list[DocumentInfo]:
    return [DocumentInfo(**doc) for doc in list_documents()]


@router.delete("/documents/{filename}", status_code=204)
def remove_document(filename: str) -> Response:
    safe_name = Path(filename).name
    if delete_document(safe_name) == 0:
        raise HTTPException(status_code=404, detail=f"No indexed document named {safe_name}.")
    (get_settings().upload_dir / safe_name).unlink(missing_ok=True)
    return Response(status_code=204)
