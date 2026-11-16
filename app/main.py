import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, documents, upload
from app.config import ROOT_DIR, get_settings
from app.services.vectorstore import get_vectorstore

FRONTEND_DIR = ROOT_DIR / "frontend"

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_vectorstore()
    yield


app = FastAPI(
    title="College Knowledge Assistant",
    description=(
        "RAG backend: upload college PDFs, then ask questions. "
        "Answers cite source document and page number."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(upload.router)
app.include_router(documents.router)
app.include_router(chat.router)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def landing_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app", include_in_schema=False)
def assistant_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
