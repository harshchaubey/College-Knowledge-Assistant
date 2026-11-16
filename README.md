# College Knowledge Assistant

Ask questions about your college PDFs (handbooks, syllabi, policies, notices) and get answers grounded in those documents, with the **document name and page number** for every source.

Built with **FastAPI, LangChain, ChromaDB, Sentence Transformers and Google Gemini**, plus a lightweight vanilla HTML/CSS/JS frontend.

---

## Features

- Landing page (`/`) and chat app (`/app`)
- Drag-and-drop PDF upload with size and type validation
- Re-uploading a PDF with the same name replaces its old chunks (no duplicates)
- Document list with chunk/page counts and delete
- Chat with formatted answers and expandable sources (document, page, snippet)
- Local embeddings (Sentence Transformers); only the final answer step calls Gemini
- Persistent vector store (ChromaDB on disk)
- Docker image with the embedding model baked in, health check, non-root user

---

## How it works

```
UPLOAD (ingest)                          CHAT (query)
PDF file                                 User question
  -> extract text per page                 -> embed question
  -> split into overlapping chunks         -> top-k similar chunks from Chroma
  -> embed with Sentence Transformers      -> context + question to Gemini
  -> store vectors + metadata in Chroma    -> answer + sources (document, page)
```

---

## Project structure

```
college-knowledge-assistant/
├── app/
│   ├── main.py              FastAPI app, routers, static files, /health
│   ├── config.py            Settings loaded from .env
│   ├── api/
│   │   ├── upload.py        POST /upload
│   │   ├── documents.py     GET /documents, DELETE /documents/{filename}
│   │   └── chat.py          POST /chat
│   ├── services/
│   │   ├── pdf_loader.py    PDF -> one Document per page
│   │   ├── chunker.py       RecursiveCharacterTextSplitter
│   │   ├── embeddings.py    HuggingFace / Sentence Transformers
│   │   ├── vectorstore.py   ChromaDB add / search / list / delete
│   │   └── llm.py           Prompt + Gemini call
│   └── schemas/models.py    Request and response models
├── frontend/
│   ├── index.html           Landing page
│   ├── app.html             Chat app
│   ├── css/                 base.css, landing.css, app.css
│   └── js/                  upload.js, chat.js
├── data/                    uploads/ and chroma/ (git-ignored)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Run locally

Requires Python 3.12 (3.10+ should work).

```bash
cd college-knowledge-assistant
python3 -m venv .venv
source .venv/bin/activate

pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

cp .env.example .env
```

Install the CPU build of PyTorch first. Otherwise pip pulls the multi-GB CUDA build.

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) and put it in `.env`:

```env
GEMINI_API_KEY=your_real_key
```

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

| URL | What |
|-----|------|
| http://localhost:8000/ | Landing page |
| http://localhost:8000/app | Chat app |
| http://localhost:8000/docs | Interactive API docs |
| http://localhost:8000/health | Health check |

On first start the embedding model (about 90 MB) is downloaded and cached.

---

## Configuration

All settings come from environment variables (or `.env`).

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-flash-latest` | Gemini model name |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence Transformers model |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `TOP_K` | `4` | Chunks retrieved per question |
| `MAX_UPLOAD_MB` | `20` | Maximum PDF size |
| `CORS_ORIGINS` | empty | Comma-separated origins; only needed if the frontend is hosted on a different domain |
| `CHROMA_DIR` | `data/chroma` | Vector store directory |
| `UPLOAD_DIR` | `data/uploads` | Uploaded PDFs directory |

If you change `EMBEDDING_MODEL`, `CHUNK_SIZE` or `CHUNK_OVERLAP`, delete `data/chroma/` and re-upload your PDFs. Vectors from different models can't be mixed.

---

## API

### `POST /upload`

Multipart form with a `file` field (PDF only).

```bash
curl -F "file=@handbook.pdf" http://localhost:8000/upload
```

```json
{
  "message": "PDF ingested successfully.",
  "filename": "handbook.pdf",
  "pages": 12,
  "chunks": 47,
  "replaced": false
}
```

| Status | When |
|--------|------|
| 400 | Not a PDF, empty file, unreadable PDF, or no extractable text (scanned) |
| 413 | Larger than `MAX_UPLOAD_MB` |
| 500 | Indexing failed |

### `GET /documents`

```json
[{ "filename": "handbook.pdf", "pages": 12, "chunks": 47 }]
```

### `DELETE /documents/{filename}`

Removes the document's chunks and the stored file. Returns `204`, or `404` if the document doesn't exist.

### `POST /chat`

```bash
curl -H "Content-Type: application/json" \
  -d '{"question": "What is the attendance policy?"}' \
  http://localhost:8000/chat
```

```json
{
  "answer": "Students must maintain at least 75% attendance...",
  "sources": [
    { "document": "handbook.pdf", "page": 14, "snippet": "Attendance: A minimum of 75%..." }
  ]
}
```

| Status | When |
|--------|------|
| 400 | Question is only whitespace |
| 422 | Missing question or longer than 1000 characters |
| 503 | `GEMINI_API_KEY` not configured |
| 502 | Gemini request failed |

If no documents are indexed, `/chat` returns a friendly message without calling Gemini.

### `GET /health`

Returns `{"status": "ok"}`.

---

## Run with Docker

The image installs CPU-only PyTorch, bakes the embedding model in at build time, runs as a non-root user (uid 1000) and listens on `$PORT` (default `8000`).

### Docker Compose (recommended)

```bash
docker compose up -d --build
docker compose logs -f
```

Data is stored in the `app-data` named volume, so uploads and the vector store survive restarts and rebuilds. Stop with `docker compose down`. Add `-v` to also delete the data.

### Plain Docker

```bash
docker build -t college-knowledge-assistant .
docker run -d --name college-assistant \
  -p 8000:8000 --env-file .env \
  -e CHROMA_DIR=/app/data/chroma -e UPLOAD_DIR=/app/data/uploads \
  -v college-data:/app/data \
  college-knowledge-assistant
```

The image is about 2 GB. Measured memory use is about 440 MB idle and about 490 MB after an upload and a chat, so plan for **at least 1 GB of RAM**.

---

## Deployment

Every option needs the same three things:

1. Set `GEMINI_API_KEY` as a secret or environment variable. Never commit `.env`.
2. Give the app at least 1 GB of RAM. 512 MB plans run out of memory.
3. Mount persistent storage at `/app/data`. Without it, uploaded documents are lost on every restart or redeploy.

### Option A: VPS (most control)

On any Linux server with Docker installed:

```bash
git clone <your-repo-url> && cd college-knowledge-assistant
cp .env.example .env
docker compose up -d --build
```

Put a reverse proxy such as Caddy or Nginx in front for HTTPS. For example, a Caddyfile:

```
your-domain.com {
    reverse_proxy localhost:8000
}
```

### Option B: Hugging Face Spaces (free Docker hosting)

1. Create a new Space and choose the **Docker** SDK.
2. Push this repository to the Space. Add this front matter at the very top of the Space's `README.md`:

   ```yaml
   ---
   title: College Knowledge Assistant
   sdk: docker
   app_port: 8000
   ---
   ```

3. In **Settings > Variables and secrets**, add the secret `GEMINI_API_KEY`.

Spaces run containers as uid 1000, which matches the image. The free tier's disk is temporary, so indexed documents are wiped when the Space restarts unless you add persistent storage.

### Option C: Render, Railway, Fly.io and similar

Deploy from the `Dockerfile`. These platforms set `$PORT` automatically, and the container uses it. Choose an instance with at least 1 GB of RAM, attach a persistent disk or volume at `/app/data`, add `GEMINI_API_KEY`, and use `/health` as the health check path.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No extractable text" on upload | The PDF is scanned images. Run OCR on it first (for example `ocrmypdf in.pdf out.pdf`). |
| 503 "GEMINI_API_KEY is missing" | Set `GEMINI_API_KEY` in `.env` or in the host's secrets, then restart. |
| 502 from `/chat` | Check the key is valid, the model name exists, and you're within the Gemini quota. The detail message contains Gemini's error. |
| pip downloads huge CUDA packages | Install the CPU PyTorch build first (see Run locally). |
| Container killed or restarting | Not enough memory. Use at least 1 GB of RAM. |
| Documents disappear after redeploy | Mount persistent storage at `/app/data`. |
| Answers ignore a newly uploaded PDF | Check it appears in the document list. Re-upload it to re-index. |

---

## Known limitations

- No authentication: anyone with the URL can upload, delete and chat. Add auth before exposing it publicly.
- Scanned PDFs need OCR before upload.
- Single shared collection for all documents.
- Answers are returned all at once, not streamed.
- Single-process app. Run one instance per data volume, because ChromaDB's local mode isn't built for multiple writers.
