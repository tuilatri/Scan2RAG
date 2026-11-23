"""End-to-end ingestion pipeline runner with GPU OCR streaming and normalization.

Iterates over PDFs in data/raw/, runs inspection, extracts text/OCR via GPU,
normalizes Vietnamese text, parses statutory structure, and exports structured JSON to data/processed/.
"""

import gc
import json
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pymupdf
from app.ingestion.image_preprocessor import ImagePreprocessor
from app.ingestion.ocr_engine import OCREngine
from app.ingestion.pdf_inspector import PageType, PDFInspector
from app.ingestion.pdf_renderer import PDFRenderer
from app.ingestion.structure_parser import LegalStructureParser
from app.ingestion.text_normalizer import TextNormalizer
from app.models.document_schema import DocumentNode, ParsedDocument

# Singleton engines to avoid re-init overhead on GPU and RAM
_ocr_engine: OCREngine | None = None
_preprocessor: ImagePreprocessor | None = None
_normalizer: TextNormalizer | None = None


def get_ocr_engine() -> OCREngine:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine(use_gpu=True)
    return _ocr_engine


def get_preprocessor() -> ImagePreprocessor:
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = ImagePreprocessor()
    return _preprocessor


def get_normalizer() -> TextNormalizer:
    global _normalizer
    if _normalizer is None:
        _normalizer = TextNormalizer()
    return _normalizer


def process_document(
    pdf_path: Path,
    output_dir: Path,
    max_pages: int | None = None,
    enable_ocr: bool = True,
):
    doc_id = pdf_path.stem.lower()
    doc_name = pdf_path.stem.replace("_", " ")

    print(f"\nProcessing: {doc_name} ({pdf_path.name})")
    inspector = PDFInspector(min_char_threshold=100)
    inspection_res = inspector.inspect_document(pdf_path)
    print(
        f"  Total pages: {inspection_res.total_pages} (Scanned: {inspection_res.scanned_pages}, Digital: {inspection_res.digital_pages}, Mixed: {inspection_res.mixed_pages})"
    )

    doc = pymupdf.open(str(pdf_path))
    parser = LegalStructureParser(document_id=doc_id, document_name=doc_name)
    normalizer = get_normalizer()
    preprocessor = get_preprocessor()
    renderer = PDFRenderer(dpi=300)

    all_nodes: list[DocumentNode] = []
    pages_to_process = len(doc) if max_pages is None else min(max_pages, len(doc))

    for page_idx in range(pages_to_process):
        page_num = page_idx + 1
        page_info = inspection_res.pages[page_idx]

        raw_text = doc[page_idx].get_text()
        digital_lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        if (
            page_info.page_type == PageType.SCANNED_IMAGE or len(digital_lines) < 5
        ) and enable_ocr:
            print(f"    Page {page_num}: Running OCR on GPU...")
            ocr_engine = get_ocr_engine()

            # Render single page to image (Streaming generator pattern)
            bgr_image = renderer.render_page(doc[page_idx])
            processed_img, _ = preprocessor.preprocess(bgr_image)

            # OCR inference
            ocr_res = ocr_engine.extract_text(processed_img, page_number=page_num)

            # Free image memory immediately
            del bgr_image
            del processed_img
            gc.collect()

            raw_lines = [b.text for b in ocr_res.blocks if b.confidence >= 0.5]
        else:
            raw_lines = digital_lines

        # Normalize Vietnamese text and legal structures
        normalized_lines = [
            normalizer.normalize(line) for line in raw_lines if line.strip()
        ]

        nodes = parser.parse_lines(normalized_lines, page_number=page_num)
        all_nodes.extend(nodes)

    doc.close()

    parsed_doc = ParsedDocument(
        document_id=doc_id,
        document_name=doc_name,
        total_pages=len(inspection_res.pages),
        nodes=all_nodes,
        summary_stats={
            "nodes_count": len(all_nodes),
            "processed_pages": pages_to_process,
        },
    )

    out_file = output_dir / f"{doc_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(parsed_doc.model_dump(), f, ensure_ascii=False, indent=2)

    print(f"  Exported {len(all_nodes)} nodes to {out_file}")


def main():
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Specific targeted run: Thông tư 68 (6 scanned pages)
    tt68_path = raw_dir / "Thông_tư_68.pdf"
    if tt68_path.exists():
        print("=== Processing target: Thông tư 68 (Full 6 scanned pages) ===")
        process_document(tt68_path, processed_dir, max_pages=None, enable_ocr=True)
    else:
        print(f"File {tt68_path} not found.")


if __name__ == "__main__":
    main()
