from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_pdf(file_path: Path) -> list[Document]:
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    loader = PyPDFLoader(str(file_path))
    pages = loader.load()

    for doc in pages:
        page_zero = doc.metadata.get("page", 0)
        doc.metadata["source"] = file_path.name
        doc.metadata["page"] = int(page_zero) + 1

    return pages
