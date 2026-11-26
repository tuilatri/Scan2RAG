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

### `backend/app/agents/` — LangGraph compare workflow (additive)

| File | Lines | Role |
|---|---:|---|
| `backend/app/agents/__init__.py` | 1 | Package marker for additive agentic workflows |
| `backend/app/agents/state.py` | 20 | `CompareState` TypedDict for the compare graph |
| `backend/app/agents/planner.py` | 98 | Opt-in LLM planner (whitelist + JSON parse + deterministic fallback) |
| `backend/app/agents/verification.py` | 12 | Numeric grounding: reject numbers in answer absent from cited evidence |
| `backend/app/agents/compare_graph.py` | 211 | Graph: plan → retrieve → evidence_check → retry → resolve_versions → synthesize → verify_answer (opt-in checkpointer) |

## Data & Benchmarks State (Milestone 1)
- `data/raw/`: 5 original legal PDFs (287 pages).
- `data/processed/`: 5 structured JSON corpora, 6.786 nodes, 111 Markdown tables (100% rectified).
- `data/benchmarks/ocr_comparison/`: Benchmark metrics (`qwen3_vl_4b_report.json`, `benchmark_summary.json`).

## Conventions
- Line counts: non-empty lines (`git ls-files` + count non-empty lines)
- Numbers use dot thousands-separators: "5.670" = 5670
