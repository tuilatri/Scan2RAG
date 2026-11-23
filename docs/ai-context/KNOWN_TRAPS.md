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

## 4. Toy Test vs Real Corpus Safeguard Trap
- **Symptom**: Safeguard pass 100% in unit tests but lets 7/13 tables lose numbers in production corpus.
- **Root cause**: Mock test used a toy 4-number list `["1", "2", "3", "4"]`. Dropping 1 number is a 25% drop (caught by 10% tolerance). But in real TT 105 tables with 48 numbers, dropping 1-4 numbers is <= 8.3% drop (silently bypassed).
- **Fix**: Zero tolerance number invariant with `collections.Counter(orig) == Counter(rect)` (0% drop, 0% added). Unit tests MUST include realistic fixtures with >=40 numbers, diopters, `%`, and military grades (`1T-6T`).

## 5. Silent Metadata Contract Drift
- **Symptom**: Audit script reports "0 safeguard breaches" even when data has errors, or fails to detect rectified tables.
- **Root cause**: Free-form dictionary keys (`dict.get("key")`) drifted between generator (`vlm_rectified`) and auditor (`rectified_by`), causing silent bypass.
- **Fix**: Enforce Pydantic schema (`TableMetadata`) with typed models and mandatory `corpus-audit` gate inside `kit.config.json`.

