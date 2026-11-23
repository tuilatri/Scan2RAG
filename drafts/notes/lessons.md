# lessons.md — Scan2RAG

> Working memory & historical operational traps. Format: ## N. Trap title (Symptom -> Root Cause -> Fix).

## 1. 4GB VRAM Out Of Memory (OOM)
- **Symptom**: CUDA memory exhaustion when running PaddleOCR + Embedding + Local LLM simultaneously.
- **Root Cause**: RTX 3050 Ti VRAM limit (4GB).
- **Fix**: Decouple offline ingestion from online serving. Run OCR/Embeddings first, then spin down before starting local LLM in LM Studio.

## 2. Table Layout Deconstruction
- **Symptom**: Multi-column medical criteria tables (Thông tư 105) lose line alignment.
- **Root Cause**: Horizontal scan without layout segmentation.
- **Fix**: Use Docling/Table Transformer to structure tables into Markdown/HTML before chunking.

## 3. Statutory Version Drift
- **Symptom**: Answering with outdated Thông tư 105 provisions instead of Thông tư 106 amendments.
- **Root Cause**: Lack of temporal version metadata.
- **Fix**: Primary retrieval targets Consolidated Document (VBHN 88); tag chunks with active/superseded status.
