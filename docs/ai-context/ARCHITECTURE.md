# ARCHITECTURE — Scan2RAG

> Overall architecture for Scan2RAG (Vietnamese Document Intelligence).
> Detailed specifications: see `docs/project-blueprint-and-specs.md` and `README.md`.

## 1. Stack & Apps
- **Backend**: Python 3.10+, FastAPI.
- **Frontend**: React + TypeScript.
- **Document Processing**: PyMuPDF, OpenCV, PaddleOCR. (Docling: planned, not implemented.)
- **Vector DB**: Qdrant (implemented). PostgreSQL: planned, not implemented (only `DATABASE_URL_TEST` / `DATABASE_URL_PRODUCTION` placeholders exist).
- **LLM Engine**: LM Studio (Local `http://localhost:1234/v1`), Groq API, OpenRouter, Gemini (cloud fallback chain).

## 2. Services & Modules
- `ingestion/`: PDF inspector, image preprocessing (deskew, denoise), OCR extraction, OCR review interface.
- `chunking/`: Structure-aware (Chương - Điều - Khoản - Điểm) & Parent-Child chunking.
- `embeddings/` & `retrieval/`: `multilingual-e5-small` / `BGE-M3`, BM25 sparse search, RRF fusion, Cross-Encoder reranker.
- `llm/`: Model router (implemented). `agents/`: LangGraph multi-document agentic search & evidence checker — planned, not implemented.

## 3. Data Layer (schema, DB convention)
- PostgreSQL (planned, not implemented): `documents`, `document_relationships`, `document_pages`, `ocr_results`, `ocr_corrections`, `conversations`.
- Qdrant: collection `vietnamese_legal_docs` with payload metadata (article, clause, version, page).

## 4. API Surface
- FastAPI REST API endpoints: Document upload, OCR verification, Search/Query, Chat stream with citations.

## 5. Security (auth, secrets, rate limits)
- Environment-based credentials via `.env` (`GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`). `DATABASE_URL_TEST` / `DATABASE_URL_PRODUCTION` are placeholders for the planned (not implemented) PostgreSQL layer.
- No sensitive user data or unverified large binary PDFs committed to Git.

## 6. Integrations
- LM Studio (OpenAI-compatible server at `http://localhost:1234/v1`).
- Groq Cloud API, OpenRouter API.
- Langfuse (optional observability).

## 7. Known Limits & Constraints
- Development environment: Laptop RTX 3050 Ti (4GB VRAM). Ingestion (OCR/Embedding) and Serving (LLM) must be phased to prevent OOM.
- Max local model size: Qwen2.5 1.5B/3B quantized GGUF. Heavy multi-hop queries routed to Groq/OpenRouter.
