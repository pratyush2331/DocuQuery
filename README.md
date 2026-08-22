# DocuQuery

A Retrieval-Augmented Generation (RAG) application that lets you upload a PDF and ask questions about it in natural language. Answers are grounded strictly in the document's content and come with page-level source citations, so every claim can be traced back to the exact text it came from.

Runs entirely on local, open-source models via [Ollama](https://ollama.com) — no API costs, no external dependency on a paid LLM provider.

**Stack:** FastAPI · React + TypeScript · ChromaDB · PyMuPDF · Ollama

---

## Why I built this

I come from a backend engineering background (Node.js, TypeScript, Kafka, MongoDB, Couchbase) and wanted to get real, hands-on depth in GenAI/RAG systems rather than just calling a wrapped `.chat()` method. So this project deliberately keeps every stage of the pipeline explicit and inspectable:

```
question → embed → vector similarity search → top-K chunks
         → build context → build prompt → call LLM → answer + citations
```

Nothing here is hidden behind a single framework call. Chunking, embedding, retrieval, and prompt construction are each their own service, independently testable and independently swappable.

## What it does

- Upload a PDF; it's validated, text-extracted page by page, chunked, embedded, and indexed into a vector store — all synchronously, with status tracking (`UPLOADED → PROCESSING → COMPLETED/FAILED`) surfaced to the frontend.
- Ask a question about the document. The system embeds the question, retrieves the most semantically relevant chunks, and passes them to the LLM as grounding context — never relying on the model's own trained-in knowledge.
- Every answer displays its source chunks (document name, page number, similarity score), expandable for inspection.
- If the answer isn't in the document, the system says so explicitly instead of guessing. This is enforced both by prompt design and by a dedicated automated test.

## Architecture

```
┌─────────────┐      REST/JSON       ┌─────────────────────┐
│   React     │ ───────────────────► │   FastAPI backend    │
│ (Vite + TS) │ ◄─────────────────── │                       │
└─────────────┘                      └──────────┬────────────┘
                                                 │
                ┌───────────────┬────────────────┼───────────────┬───────────────┐
                ▼               ▼                ▼               ▼               ▼
         ┌─────────────┐ ┌─────────────┐  ┌──────────────┐ ┌────────────┐ ┌──────────────┐
         │ PDF Service │ │ Chunking Svc│  │ Embedding Svc│ │  ChromaDB  │ │  LLM Service │
         │ (PyMuPDF)   │ │             │  │  (Ollama)    │ │(persisted) │ │  (Ollama)    │
         └─────────────┘ └─────────────┘  └──────────────┘ └────────────┘ └──────────────┘
```

The embedding and LLM services are thin wrappers around the OpenAI Python SDK pointed at a local `base_url`. Swapping providers (e.g. to OpenAI, or a hosted inference API) is a two-line change in two files — the rest of the application is provider-agnostic by design.

**Ingestion pipeline:**
```
PDF upload → validation → page-aware text extraction → cleaning
  → chunking (configurable size/overlap) → embedding → vector storage
```

**Query pipeline:**
```
question → embed → similarity search (top-K, scoped to selected document)
  → context construction with source tags → prompt construction
  → LLM call → answer + deduplicated source citations
```

## Project structure

```
DocuQuery/
├── backend/
│   ├── app/
│   │   ├── main.py               # app entrypoint, CORS, router registration
│   │   ├── api/                  # documents.py, chat.py, health.py
│   │   ├── core/                 # typed settings, logging
│   │   ├── models/                # Pydantic schemas
│   │   ├── services/              # pdf, chunking, embedding, vector_store,
│   │   │                          # retrieval, llm, document_store
│   │   ├── prompts/               # RAG prompt template
│   │   └── utils/exceptions.py
│   ├── tests/                     # pytest suite, AI calls mocked
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/            # Upload, DocumentList, ChatWindow,
│       │                          # ChatMessage, SourceCard, RetrievedContext
│       ├── services/api.ts        # typed API client
│       └── App.tsx
└── docker-compose.yml
```

## Engineering decisions worth calling out

- **In-memory document store for V1.** No Postgres/Mongo — a process-lifetime store was enough to prove out the RAG pipeline without adding infrastructure that doesn't teach anything new. It's implemented behind a single class so swapping in a real database later doesn't touch the API layer.
- **Per-page chunking, not cross-page.** Every chunk carries one unambiguous page number for citation purposes. Trade-off: a paragraph that straddles a page boundary can be split even with overlap enabled — a known, documented limitation rather than a silent one.
- **Synchronous ingestion.** No Celery/Kafka/queue for V1 — deliberately avoided premature infrastructure. The pipeline is structured so async processing can be added later without a rewrite.
- **Local models over a hosted API.** Chose Ollama specifically to keep the project fully self-contained and runnable without any billing dependency, while keeping the code path identical to what a hosted OpenAI-compatible API would use.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com/download)

### 1. Install Ollama and pull models

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

`llama3.2` handles answer generation, `nomic-embed-text` handles embeddings. One-time download (~2.3GB total); runs fully offline afterward.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

In `backend/.env`:
```
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2
EMBEDDING_MODEL=nomic-embed-text
```

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

### 4. Tests

```bash
cd backend
pytest tests/ -v
```

26 tests, all AI calls mocked with a deterministic fake embedding function — the suite exercises real chunking, real ChromaDB storage/retrieval, and the full API layer without needing Ollama or any external service running.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/documents/upload` | Upload and process a PDF |
| GET | `/api/documents` | List all documents |
| GET | `/api/documents/{id}` | Get a document's status |
| DELETE | `/api/documents/{id}` | Delete a document and its vectors |
| POST | `/api/chat/query` | `{document_id, question}` → `{answer, sources, retrieved_chunks}` |

## Environment variables

| Variable | Purpose |
|---|---|
| `LLM_MODEL` / `EMBEDDING_MODEL` | Which Ollama models to use |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunking granularity and boundary overlap |
| `TOP_K` | Number of chunks retrieved per query |
| `CHROMA_PERSIST_DIRECTORY` | Where vector data is stored on disk |
| `MAX_FILE_SIZE_MB` | Upload size limit |
| `FRONTEND_URL` | CORS origin |

## Roadmap / known limitations

Explicitly out of scope for this version, but the codebase is structured to support them without a rewrite: multi-document RAG, hybrid/keyword+vector search, reranking, query rewriting, server-side conversation persistence, streaming responses, OCR for scanned PDFs, and authentication.

## Docker

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:5173`. Not required for local development.
