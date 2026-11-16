"""
Step 7b — Chat / RAG pipeline
-----------------------------
POST /chat
  1. Embed the question (handled inside Chroma)
  2. Retrieve top-k relevant chunks
  3. Send context + question to Gemini
  4. Return answer + source document/page
"""

from fastapi import APIRouter, HTTPException

from app.schemas.models import ChatRequest, ChatResponse, Source
from app.services.llm import answer_with_context
from app.services.vectorstore import similarity_search

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # 1–2) Retrieve relevant chunks from Chroma
        docs = similarity_search(question)

        # 3) Ask Gemini with that context
        answer = answer_with_context(question, docs)
    except ValueError as exc:
        # Missing API key, etc.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc

    # 4) Build source list (document + page)
    sources: list[Source] = []
    seen: set[tuple[str, int]] = set()
    for doc in docs:
        document = str(doc.metadata.get("source", "unknown"))
        page = int(doc.metadata.get("page", 0) or 0)
        key = (document, page)
        if key in seen:
            continue
        seen.add(key)
        snippet = doc.page_content.strip().replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        sources.append(Source(document=document, page=page, snippet=snippet))

    return ChatResponse(answer=answer, sources=sources)
