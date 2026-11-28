# MODULE_MAP — Scan2RAG

> Source of truth for repo structure. Line counts = non-empty (TESTING_GUIDE §1 convention).
> doc-truth.mjs parses the table below: `| \`path\` | number |` — keep the format when editing.

## Backend — FastAPI / Python · Ingestion Pipeline (Milestone 1 Complete)

### `backend/app/ingestion/` — Document Ingestion & OCR Processing

| File | Lines | Role |
|---|---:|---|
| `backend/app/ingestion/image_preprocessor.py` | 85 | OpenCV deskew, denoise, adaptive thresholding |
| `backend/app/ingestion/ocr_engine.py` | 65 | PaddleOCR Vietnamese text detection & recognition |
| `backend/app/ingestion/pdf_inspector.py` | 79 | PyMuPDF text/scan inspection & page metadata |
| `backend/app/ingestion/pdf_renderer.py` | 29 | PyMuPDF high-DPI page rendering to PNG/bytes |
| `backend/app/ingestion/structure_parser.py` | 164 | Legal hierarchy parser (Chương - Điều - Khoản - Điểm) |
| `backend/app/ingestion/table_extractor.py` | 185 | OCR bounding-box clustering to Markdown table |
| `backend/app/ingestion/text_normalizer.py` | 128 | Unicode NFC normalization & Vietnamese diacritics |
| `backend/app/ingestion/vlm_rectifier.py` | 149 | Multi-modal VLM table rectification with Counter safeguard |
| `backend/app/ingestion/table_structure.py` | 69 | Header-aware score-column parsing + standalone OCR score rows (inspired by SLANet layer) |
| `backend/app/ingestion/vietnamese_corrector.py` | 88 | Deterministic OCR correction with phrase-level passes and curated dictionary (inspired by ProtonX, not the model) |
| `backend/app/ingestion/correction_dictionary.json` | 38 | Tracked domain pairs + identity locks for protected legal phrases |
| `backend/app/ingestion/ocr_pipeline.py` | 45 | Adapter: preprocess → OCR → correct → structure; engine swappable |

### `backend/app/agents/` — LangGraph compare workflow (additive)

| File | Lines | Role |
|---|---:|---|
| `backend/app/agents/__init__.py` | 1 | Package marker for additive agentic workflows |
| `backend/app/agents/state.py` | 20 | `CompareState` TypedDict for the compare graph |
| `backend/app/agents/planner.py` | 98 | Opt-in LLM planner (whitelist + JSON parse + deterministic fallback) |
| `backend/app/agents/verification.py` | 12 | Numeric grounding: reject numbers in answer absent from cited evidence |
| `backend/app/agents/compare_graph.py` | 211 | Graph: plan → retrieve → evidence_check → retry → resolve_versions → synthesize → verify_answer (opt-in checkpointer) |

### `backend/app/guards/` — Deterministic pre-LLM guards

| File | Lines | Role |
|---|---:|---|
| `backend/app/guards/__init__.py` | 1 | Package marker |
| `backend/app/guards/scope_guard.py` | 74 | Out-of-scope detection; in-scope legal/medical hints win |

### `backend/app/services/` — Grounded QA orchestration

| File | Lines | Role |
|---|---:|---|
| `backend/app/services/qa_service.py` | 333 | Hybrid retrieval → rerank → citations → SSE; scope guard; top-k table fallback; statutory version notes |

### `backend/app/retrieval/` — Vector + BM25 + rerank

| File | Lines | Role |
|---|---:|---|
| `backend/app/retrieval/hybrid_searcher.py` | 208 | Dense Qdrant + sparse BM25 via RRF; `table_chunks_for(document_id)`; carries `superseded_by`/`effective_date` |
| `backend/app/retrieval/reranker.py` | 92 | Cross-encoder; boosts score tables, and first-window table on location questions |
| `backend/app/retrieval/qdrant_client.py` | 125 | Remote Qdrant client with local disk DEGRADED fallback |

### `backend/app/canonical/` — Layer-A fact store (pilot)

| File | Lines | Role |
|---|---:|---|
| `backend/app/models/canonical_fact.py` | 37 | `CanonicalFact` / `CanonicalRule` schema with `evidence_image`, `needs_human`, `authoritative` |
| `backend/app/canonical/__init__.py` | 1 | Package marker |
| `backend/app/canonical/store.py` | 24 | Load + invariants: no fake authoritative, no duplicate id |

### `scripts/canonical` — Pilot fact extraction & audit

| File | Lines | Role |
|---|---:|---|
| `scripts/build_canonical_facts.py` | 141 | Scan all 111 tables, render 200 DPI evidence, parse score rows via `table_structure` + 3 guidance rules |
| `scripts/ingest_docx_facts.py` | 166 | Read external VietNamOCR DOCX grid, map tables to doc/page with used-context de-dup, emit DOCX-sourced facts |
| `scripts/audit_canonical_facts.py` | 61 | Local gate over both stores: evidence exists, no authoritative without human decision |
| `scripts/review_canonical_fact.py` | 79 | Human review CLI: agent cannot approve; writes review_decisions.json |
| `scripts/benchmark_ocr_engines.py` | 309 | Phase-0 OCR benchmark: page-scoped DOCX reference, number-signature fuzzy match, CER/WER, score-cell, number retention |
| `scripts/derive_corrections.py` | 109 | Derive correction proposals from OCR↔DOCX fact pairs; --apply writes tracked dictionary |

## Data & Benchmarks State (Milestone 1)
- `data/raw/`: 5 original legal PDFs (287 pages).
- `data/processed/`: 5 structured JSON corpora, 6.786 nodes, 111 Markdown tables (100% rectified).
- `data/benchmarks/ocr_comparison/`: Benchmark metrics (`qwen3_vl_4b_report.json`, `benchmark_summary.json`).

## Conventions
- Line counts: non-empty lines (`git ls-files` + count non-empty lines)
- Numbers use dot thousands-separators: "5.670" = 5670
