# KNOWN_TRAPS — Scan2RAG

> Pitfalls already hit — record them so they never repeat. Format: ## N. trap name + explanation + fix.

## 1. 4GB VRAM Out Of Memory (OOM) trap
- **Symptom**: CUDA out of memory error when running OCR, Embeddings, and Local LLM simultaneously.
- **Root cause**: RTX 3050 Ti has only 4GB VRAM. PaddleOCR + BGE-M3 + LLM loaded in memory exceeds capacity.
- **Fix**: Phase execution: run Ingestion (OCR + Embedding) offline; free memory before starting Serving (LM Studio LLM). In LM Studio, restrict local model to Qwen2.5 1.5B/3B quantized Q4_K_M with partial GPU offloading.

## 2. Medical Classification Table structure break in OCR
- **Symptom**: Line-by-line OCR scrambles row-column association in Annexes (Thông tư 105 health criteria tables).
- **Root cause**: Multi-column table layout not preserved by naive horizontal OCR scanning.
- **Fix**: Use layout parsing (Docling / Table Transformer) to convert tables into Markdown/HTML tables before chunking, and utilize human-in-the-loop validation for crucial medical tables.

## 3. Statutory Supersession / Temporal Collision
- **Symptom**: LLM cites obsolete regulations from TT 105 instead of amended rules from TT 106.
- **Root cause**: Naive similarity search retrieves both documents without version context.
- **Fix**: Primary search targets Consolidated Document (VBHN 88); tag chunks with `is_superseded` and `effective_date` metadata.

