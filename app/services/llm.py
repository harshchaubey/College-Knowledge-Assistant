from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings

SYSTEM_PROMPT = """You are a College Knowledge Assistant.
Answer the user's question using ONLY the context excerpts below.
If the context does not contain enough information, say you do not know
based on the uploaded documents. Be concise and clear.
When useful, mention which document/page the fact came from.
"""


def _format_context(docs: list[Document]) -> str:
    parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        parts.append(
            f"[Excerpt {i}] (document={source}, page={page})\n{doc.page_content}"
        )
    return "\n\n".join(parts) if parts else "(no relevant context found)"


def get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key.startswith("your_"):
        raise ValueError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and set your key."
        )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.2,
    )


def answer_with_context(question: str, docs: list[Document]) -> str:
    llm = get_llm()
    context = _format_context(docs)
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )
    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
    )
    return response.text.strip()
