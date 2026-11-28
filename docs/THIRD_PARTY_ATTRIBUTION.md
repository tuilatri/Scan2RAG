# Third-party attribution

## VietNamOCR 3.3.1 (external OCR source and architectural reference)

`drafts/outsource/ocr-result.docx` was produced by **VietNamOCR 3.3.1**, by **VVT** (moniter.io.vn), Copyright 2026 VVT. This project uses the resulting DOCX as a higher-quality input for score tables and studies the tool's architecture. **No binary, protected model, or obfuscated file from the VietNamOCR portable package is copied into this repository.**

The reference tool combines:

- **Google ScreenAI / Google OCR** (`gocr`, `aksara`) for text recognition.
- **SLANet-plus and layout/table detectors exported from PaddlePaddle** for table structure.
- **ProtonX `protonx-tc-v1.4`** for Vietnamese correction, licensed **v1.4-NC (non-commercial)**.
- `python-docx` for Word export.

This repository is used for non-commercial purposes. If that changes, the ProtonX v1.4-NC terms must be reviewed again before relying on any ProtonX-derived data.

## Open components used directly by Scan2RAG

- **PaddleOCR** (`lang="vi"`) — existing Vietnamese text recognition in `backend/app/ingestion/ocr_engine.py`.
- **OpenCV** — deskew, denoise in `backend/app/ingestion/image_preprocessor.py`.
- **PyMuPDF** — PDF inspection, page rendering, evidence images.
- **Qdrant**, **FastAPI**, **React** — serving stack.

## Inspired, locally implemented layers

Inspired by the three-layer design above, this repo implements auditable open equivalents:

| Inspired layer | Local implementation | Note |
|---|---|---|
| Table structure | `backend/app/ingestion/table_structure.py` | Header-aware Markdown parsing; not SLANet |
| Vietnamese correction | `backend/app/ingestion/vietnamese_corrector.py` | Deterministic dictionary pass; **not** ProtonX model |
| Pipeline orchestration | `backend/app/ingestion/ocr_pipeline.py` | Adapter for swapping engines; defaults to PaddleOCR |

`scripts/ingest_docx_facts.py` reads the externally generated DOCX and writes canonical facts with `source_kind="docx"`; all such facts still require human review before becoming authoritative.
