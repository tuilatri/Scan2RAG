# WORKSPACE.md — Scan2RAG

> Scope folders and workspace structure reference (read-only).

- `backend/`: FastAPI application, document ingestion, chunking, retrieval, LLM router.
- `frontend/`: React TypeScript application (UI/UX).
- `data/`: Local storage for PDFs, OCR output, and exports (gitignored).
- `docs/`: Technical specifications, architecture docs, tickets, and AI context.
- `drafts/`: Working plans, notes, and session checklists (gitignored).
- `evaluation/`: Benchmark datasets, OCR CER/WER scripts, RAGAS generation evaluations.
- `scripts/`: Verification gates and pipeline utilities.
