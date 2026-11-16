import logging

from fastapi import APIRouter, HTTPException
from langchain_core.documents import Document

from app.schemas.models import ChatRequest, ChatResponse, Source
from app.services.llm import answer_with_context
from app.services.vectorstore import similarity_search

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

NO_DOCUMENTS_ANSWER = (
    "I don't have any documents to search yet. Upload a PDF first, then ask your question."
)


def build_sources(docs: list[Document]) -> list[Source]:
    sources: list[Source] = []
    seen: set[tuple[str, int]] = set()
    for doc in docs:
        document = str(doc.metadata.get("source", "unknown"))
        page = int(doc.metadata.get("page", 0) or 0)
        if (document, page) in seen:
            continue
        seen.add((document, page))
        snippet = doc.page_content.strip().replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        sources.append(Source(document=document, page=page, snippet=snippet))
    return sources


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    docs = similarity_search(question)
    if not docs:
        return ChatResponse(answer=NO_DOCUMENTS_ANSWER, sources=[])

    try:
        answer = answer_with_context(question, docs)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Gemini request failed")
        raise HTTPException(
            status_code=502, detail=f"The AI service could not answer: {exc}"
        ) from exc

    return ChatResponse(answer=answer, sources=build_sources(docs))
