from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.services.embeddings import get_embeddings


@lru_cache
def get_vectorstore() -> Chroma:
    settings = get_settings()
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.chroma_dir),
    )


def add_documents(chunks: list[Document]) -> int:
    if not chunks:
        return 0
    store = get_vectorstore()
    store.add_documents(chunks)
    return len(chunks)


def similarity_search(query: str, k: int | None = None) -> list[Document]:
    settings = get_settings()
    store = get_vectorstore()
    return store.similarity_search(query, k=k or settings.top_k)


def delete_document(source: str) -> int:
    store = get_vectorstore()
    ids = store.get(where={"source": source})["ids"]
    if ids:
        store.delete(ids=ids)
    return len(ids)


def list_documents() -> list[dict]:
    metadatas = get_vectorstore().get(include=["metadatas"])["metadatas"]
    summary: dict[str, dict] = {}
    for metadata in metadatas:
        source = str(metadata.get("source", "unknown"))
        entry = summary.setdefault(source, {"filename": source, "pages": 0, "chunks": 0})
        entry["chunks"] += 1
        pages = int(metadata.get("total_pages") or metadata.get("page") or 0)
        entry["pages"] = max(entry["pages"], pages)
    return sorted(summary.values(), key=lambda doc: doc["filename"].lower())
